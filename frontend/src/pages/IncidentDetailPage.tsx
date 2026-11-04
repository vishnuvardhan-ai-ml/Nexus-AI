import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  AlertTriangle,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
  MapPin,
  Clock,
  ShieldCheck,
  BrainCircuit,
  Sliders,
  Sparkles,
  Layers,
  CheckCircle2,
  HelpCircle,
  Building2,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getIncidentById, assessIncident, getRecommendations } from '../services/api';
import {
  Incident,
  IncidentCategory,
  RiskAssessmentResponse,
  RecommendationItem,
  RiskFactorInput,
  RiskLevel,
  FactorInfluence,
} from '../types';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user, role, token } = useAuth();

  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Intelligence Assessment State
  const [assessment, setAssessment] = useState<RiskAssessmentResponse | null>(null);
  const [loadingAssessment, setLoadingAssessment] = useState<boolean>(false);
  const [assessmentError, setAssessmentError] = useState<string | null>(null);

  // Recommendations State
  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [loadingRecs, setLoadingRecs] = useState<boolean>(false);

  // Interactive Factor Override Controls
  const [customH, setCustomH] = useState<number>(75);
  const [customE, setCustomE] = useState<number>(65);
  const [customV, setCustomV] = useState<number>(55);
  const [customD, setCustomD] = useState<number>(45);
  const [showFactorTuning, setShowFactorTuning] = useState<boolean>(false);

  // 1. Fetch Incident Record
  const fetchIncident = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getIncidentById(id, token);
      setIncident(data);

      // Initialize factor baselines from incident metadata
      const baseH = data.severity === 'HIGH' ? 80 : data.severity === 'MEDIUM' ? 50 : 25;
      const baseE = data.category === 'electrical_hazard' || data.category === 'waterlogging' ? 70 : 55;
      const baseV = data.severity === 'HIGH' ? 65 : 45;
      const baseD = 50;
      setCustomH(baseH);
      setCustomE(baseE);
      setCustomV(baseV);
      setCustomD(baseD);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not locate incident record.');
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  // 2. Fetch or Run Assessment
  const runAssessment = useCallback(async (hVal: number, eVal: number, vVal: number, dVal: number) => {
    if (!id) return;
    setLoadingAssessment(true);
    setAssessmentError(null);
    try {
      const factors: RiskFactorInput = {
        hazard_severity: hVal,
        exposure: eVal,
        vulnerability: vVal,
        duration: dVal,
        source: 'USER_DIRECT',
        source_notes: `Evaluated by analyst UID: ${user?.uid || 'authenticated_user'} on incident ${id}`,
      };

      const result = await assessIncident(
        {
          incident_id: id,
          factors,
          include_ml_advisory: true,
        },
        token
      );
      setAssessment(result);
    } catch (err: unknown) {
      setAssessmentError(err instanceof Error ? err.message : 'Failed to compute risk assessment.');
    } finally {
      setLoadingAssessment(false);
    }
  }, [id, user, token]);

  // 3. Fetch Recommendations
  const fetchRecs = useCallback(async () => {
    if (!id) return;
    setLoadingRecs(true);
    try {
      const recsRes = await getRecommendations(id, token);
      setRecommendations(recsRes.recommendations || []);
    } catch (err) {
      console.warn('Could not load recommendations:', err);
    } finally {
      setLoadingRecs(false);
    }
  }, [id, token]);

  useEffect(() => {
    fetchIncident();
    fetchRecs();
  }, [fetchIncident, fetchRecs]);

  // Run initial assessment once incident is loaded
  useEffect(() => {
    if (incident) {
      const baseH = incident.severity === 'HIGH' ? 80 : incident.severity === 'MEDIUM' ? 50 : 25;
      const baseE = incident.category === 'electrical_hazard' || incident.category === 'waterlogging' ? 70 : 55;
      const baseV = incident.severity === 'HIGH' ? 65 : 45;
      const baseD = 50;
      runAssessment(baseH, baseE, baseV, baseD);
    }
  }, [incident, runAssessment]);

  const getCategoryDetails = (cat: IncidentCategory) => {
    switch (cat) {
      case 'waterlogging':
        return { label: 'Waterlogging', icon: Droplets, color: 'text-sky-400 bg-sky-950/30 border-sky-500/40' };
      case 'road_damage':
        return { label: 'Road Damage', icon: Construction, color: 'text-amber-400 bg-amber-950/30 border-amber-500/40' };
      case 'electrical_hazard':
        return { label: 'Electrical Hazard', icon: Zap, color: 'text-yellow-400 bg-yellow-950/30 border-yellow-500/40' };
      case 'waste_management':
        return { label: 'Waste Management', icon: Trash2, color: 'text-emerald-400 bg-emerald-950/30 border-emerald-500/40' };
      case 'extreme_heat':
        return { label: 'Extreme Heat', icon: Flame, color: 'text-rose-400 bg-rose-950/30 border-rose-500/40' };
    }
  };

  const getInfluenceBadge = (influence: FactorInfluence) => {
    switch (influence) {
      case 'AMPLIFYING':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/40">AMPLIFYING</span>;
      case 'DAMPENING':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">DAMPENING</span>;
      case 'NEUTRAL':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-800 text-slate-300">NEUTRAL</span>;
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'IMMEDIATE':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-500/50 animate-pulse">IMMEDIATE</span>;
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/60 text-amber-300 border border-amber-500/40">HIGH PRIORITY</span>;
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-sky-950/60 text-sky-300 border border-sky-500/40">MEDIUM</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-slate-900 text-slate-400 border border-slate-700/40">MONITOR</span>;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <div className="w-8 h-8 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
        <p className="text-xs font-mono text-slate-400">LOADING INCIDENT RECORD...</p>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="max-w-xl mx-auto my-12 p-8 glass-panel rounded-xl border border-rose-800/40 text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Incident Not Found</h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          The requested incident record was not found or has been restricted under role-based authorization rules.
        </p>
        <Link to="/incidents">
          <Button variant="secondary" size="sm">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Incident Stream
          </Button>
        </Link>
      </div>
    );
  }

  const catDetails = getCategoryDetails(incident.category);
  const CategoryIcon = catDetails.icon;
  const isReporter = user?.uid === incident.reported_by;

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-16">
      {/* Top Breadcrumb Navigation */}
      <div className="flex items-center justify-between pb-4 border-b border-navy-800">
        <Link
          to="/incidents"
          className="inline-flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-brand-cyan transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>BACK TO INCIDENT STREAM</span>
        </Link>

        <div className="flex items-center gap-2">
          {isReporter && (
            <Badge variant="cyan" dot>
              YOUR REPORT
            </Badge>
          )}
          <Badge
            variant={
              incident.severity === 'HIGH'
                ? 'high'
                : incident.severity === 'MEDIUM'
                ? 'medium'
                : 'low'
            }
            dot
          >
            {incident.severity} SEVERITY
          </Badge>
          <Badge variant="neutral">
            {incident.status}
          </Badge>

          {(role === 'ANALYST' || role === 'ADMIN') && (
            <Link to={`/mitigation-planner?incident_id=${incident.id}`}>
              <Button size="sm" variant="secondary" className="gap-1.5 text-xs h-7 ml-2">
                <Layers className="w-3.5 h-3.5 text-brand-cyan" />
                <span>Plan Mitigation</span>
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Main Incident Overview Card */}
      <div className="glass-panel rounded-xl p-6 sm:p-8 border border-navy-800 space-y-6 shadow-glow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-navy-800/80">
          <div className="flex items-start sm:items-center gap-3">
            <div className={`p-3 rounded-xl border ${catDetails.color} shrink-0`}>
              <CategoryIcon className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-mono text-brand-cyan font-semibold">
                INCIDENT ID: {incident.id}
              </span>
              <h1 className="text-xl sm:text-2xl font-bold text-white mt-0.5 tracking-tight">
                {incident.title}
              </h1>
            </div>
          </div>

          <Link to={`/simulator?incident_id=${incident.id}`}>
            <Button variant="primary" size="sm">
              <Sliders className="w-3.5 h-3.5 mr-1" />
              <span>Simulate Mitigation</span>
            </Button>
          </Link>
        </div>

        {/* Location & Time Info */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-4 rounded-xl bg-navy-900/60 border border-navy-800 text-xs">
          <div>
            <span className="text-slate-400 uppercase font-mono text-[10px] block">Location Landmark</span>
            <span className="text-slate-200 font-medium flex items-center gap-1.5 mt-1">
              <MapPin className="w-3.5 h-3.5 text-brand-cyan shrink-0" />
              <span>{incident.location}</span>
            </span>
          </div>

          <div>
            <span className="text-slate-400 uppercase font-mono text-[10px] block">GPS Coordinates</span>
            <span className="text-slate-200 font-mono mt-1 block">
              {incident.latitude && incident.longitude
                ? `${incident.latitude.toFixed(6)}, ${incident.longitude.toFixed(6)}`
                : 'No GPS data attached'}
            </span>
          </div>

          <div>
            <span className="text-slate-400 uppercase font-mono text-[10px] block">Reported Timestamp</span>
            <span className="text-slate-200 font-mono mt-1 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-500" />
              <span>{new Date(incident.created_at).toLocaleString()}</span>
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="space-y-2">
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Hazard Description & Field Observations
          </h3>
          <div className="p-4 rounded-xl bg-navy-900/40 border border-navy-800 text-sm text-slate-200 leading-relaxed whitespace-pre-line">
            {incident.description}
          </div>
        </div>

        {/* Attached Photo */}
        {incident.image_url && (
          <div className="space-y-2">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400">
              Attached Field Image
            </h3>
            <div className="rounded-xl overflow-hidden border border-navy-800 max-h-80">
              <img
                src={incident.image_url}
                alt={incident.title}
                className="w-full h-full object-cover max-h-80"
              />
            </div>
          </div>
        )}
      </div>

      {/* ===================================================================== */}
      {/* MILESTONE 3: RISK INTELLIGENCE & EXPLAINABILITY PANEL */}
      {/* ===================================================================== */}
      <div className="glass-panel rounded-xl p-6 sm:p-8 border border-brand-cyan/30 space-y-6 shadow-glow-card">
        {/* Panel Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-navy-800">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-brand-cyan/10 border border-brand-cyan/30 text-[10px] font-mono text-brand-cyan mb-1.5">
              <BrainCircuit className="w-3.5 h-3.5" />
              <span>DETERMINISTIC CIVIC INTELLIGENCE ENGINE</span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <span>Risk Intelligence Assessment</span>
              {loadingAssessment && (
                <div className="w-4 h-4 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
              )}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Transparent multi-criteria evaluation combining physical severity, population exposure, fragility, and elapsed duration.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowFactorTuning(!showFactorTuning)}
            >
              <Sliders className="w-3.5 h-3.5 mr-1" />
              <span>{showFactorTuning ? 'Hide Factors' : 'Tune Factors'}</span>
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => runAssessment(customH, customE, customV, customD)}
              disabled={loadingAssessment}
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loadingAssessment ? 'animate-spin' : ''}`} />
              <span>Re-Evaluate</span>
            </Button>
          </div>
        </div>

        {/* Factor Tuning Form (When Toggled) */}
        {showFactorTuning && (
          <div className="p-4 rounded-xl bg-navy-950/80 border border-navy-800 space-y-4">
            <div className="text-xs font-mono uppercase text-brand-cyan font-semibold flex items-center justify-between">
              <span>Analyst Factor Calibration (0–100)</span>
              <span className="text-[10px] text-slate-400">All 4 inputs required (Zero Silent Invention)</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                  Hazard Severity (H)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={customH}
                  onChange={(e) => setCustomH(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded bg-navy-900 border border-navy-800 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                  Exposure (E)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={customE}
                  onChange={(e) => setCustomE(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded bg-navy-900 border border-navy-800 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                  Vulnerability (V)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={customV}
                  onChange={(e) => setCustomV(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded bg-navy-900 border border-navy-800 text-xs text-white font-mono"
                />
              </div>

              <div>
                <label className="text-[10px] font-mono uppercase text-slate-400 block mb-1">
                  Duration (D)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={customD}
                  onChange={(e) => setCustomD(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 rounded bg-navy-900 border border-navy-800 text-xs text-white font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* Assessment Evaluation Presentation */}
        {assessment ? (
          <div className="space-y-6">
            {/* Top Score Banner */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center p-5 rounded-xl bg-navy-950/60 border border-navy-800">
              {/* Score Display (4 cols) */}
              <div className="md:col-span-4 text-center md:text-left md:border-r border-navy-800 md:pr-6 space-y-1">
                <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider block">
                  Authoritative Composite Risk Score
                </span>
                <div className="flex items-baseline justify-center md:justify-start gap-2">
                  <span className="text-4xl sm:text-5xl font-black text-white font-mono">
                    {assessment.risk_score.toFixed(1)}
                  </span>
                  <span className="text-xs font-mono text-slate-500">/ 100.0</span>
                </div>
                <div className="pt-1">
                  <Badge
                    variant={
                      assessment.risk_level === 'HIGH'
                        ? 'high'
                        : assessment.risk_level === 'MEDIUM'
                        ? 'medium'
                        : 'low'
                    }
                    dot
                  >
                    {assessment.risk_level} RISK LEVEL
                  </Badge>
                </div>
              </div>

              {/* Primary & Secondary Drivers (8 cols) */}
              <div className="md:col-span-8 space-y-3 md:pl-2">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="px-3 py-1.5 rounded-lg bg-navy-900 border border-brand-cyan/40 text-xs flex items-center gap-2">
                    <span className="text-slate-400 font-mono text-[10px] uppercase">Primary Driver:</span>
                    <span className="font-bold text-brand-cyan uppercase">
                      {assessment.contributions.primary_driver}
                    </span>
                  </div>

                  {assessment.contributions.secondary_driver && (
                    <div className="px-3 py-1.5 rounded-lg bg-navy-900 border border-navy-800 text-xs flex items-center gap-2">
                      <span className="text-slate-400 font-mono text-[10px] uppercase">Secondary Driver:</span>
                      <span className="font-bold text-slate-200 uppercase">
                        {assessment.contributions.secondary_driver}
                      </span>
                    </div>
                  )}

                  <span className="text-[10px] font-mono text-slate-500">
                    Formula: R = 0.4H + 0.3E + 0.2V + 0.1D
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  {assessment.explanation}
                </p>
              </div>
            </div>

            {/* Factor Decomposition Grid (4 Cards) */}
            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider block">
                Factor Contribution Breakdown (Weight * Input = Contributed Points)
              </span>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* 1. Hazard */}
                <div className="p-3.5 rounded-xl bg-navy-900/50 border border-navy-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">Hazard (H)</span>
                    <span className="text-[10px] font-mono text-slate-400">40% Wt</span>
                  </div>
                  <div className="flex items-baseline justify-between font-mono">
                    <span className="text-lg font-bold text-white">
                      {assessment.contributions.hazard.input_value.toFixed(0)}/100
                    </span>
                    <span className="text-xs text-brand-cyan font-bold">
                      +{assessment.contributions.hazard.weighted_points.toFixed(1)} pts
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-navy-800/80">
                    <span className="text-[10px] font-mono text-slate-400">
                      {assessment.contributions.hazard.contribution_percentage.toFixed(1)}% of Risk
                    </span>
                    {getInfluenceBadge(assessment.contributions.hazard.influence)}
                  </div>
                </div>

                {/* 2. Exposure */}
                <div className="p-3.5 rounded-xl bg-navy-900/50 border border-navy-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">Exposure (E)</span>
                    <span className="text-[10px] font-mono text-slate-400">30% Wt</span>
                  </div>
                  <div className="flex items-baseline justify-between font-mono">
                    <span className="text-lg font-bold text-white">
                      {assessment.contributions.exposure.input_value.toFixed(0)}/100
                    </span>
                    <span className="text-xs text-brand-cyan font-bold">
                      +{assessment.contributions.exposure.weighted_points.toFixed(1)} pts
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-navy-800/80">
                    <span className="text-[10px] font-mono text-slate-400">
                      {assessment.contributions.exposure.contribution_percentage.toFixed(1)}% of Risk
                    </span>
                    {getInfluenceBadge(assessment.contributions.exposure.influence)}
                  </div>
                </div>

                {/* 3. Vulnerability */}
                <div className="p-3.5 rounded-xl bg-navy-900/50 border border-navy-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">Vulnerability (V)</span>
                    <span className="text-[10px] font-mono text-slate-400">20% Wt</span>
                  </div>
                  <div className="flex items-baseline justify-between font-mono">
                    <span className="text-lg font-bold text-white">
                      {assessment.contributions.vulnerability.input_value.toFixed(0)}/100
                    </span>
                    <span className="text-xs text-brand-cyan font-bold">
                      +{assessment.contributions.vulnerability.weighted_points.toFixed(1)} pts
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-navy-800/80">
                    <span className="text-[10px] font-mono text-slate-400">
                      {assessment.contributions.vulnerability.contribution_percentage.toFixed(1)}% of Risk
                    </span>
                    {getInfluenceBadge(assessment.contributions.vulnerability.influence)}
                  </div>
                </div>

                {/* 4. Duration */}
                <div className="p-3.5 rounded-xl bg-navy-900/50 border border-navy-800 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">Duration (D)</span>
                    <span className="text-[10px] font-mono text-slate-400">10% Wt</span>
                  </div>
                  <div className="flex items-baseline justify-between font-mono">
                    <span className="text-lg font-bold text-white">
                      {assessment.contributions.duration.input_value.toFixed(0)}/100
                    </span>
                    <span className="text-xs text-brand-cyan font-bold">
                      +{assessment.contributions.duration.weighted_points.toFixed(1)} pts
                    </span>
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-navy-800/80">
                    <span className="text-[10px] font-mono text-slate-400">
                      {assessment.contributions.duration.contribution_percentage.toFixed(1)}% of Risk
                    </span>
                    {getInfluenceBadge(assessment.contributions.duration.influence)}
                  </div>
                </div>
              </div>
            </div>

            {/* Advisory Scikit-Learn Model Banner (Labeled DEMO) */}
            {assessment.ml_advisory && (
              <div className="p-4 rounded-xl bg-navy-950/70 border border-cyan-500/30 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-brand-cyan flex items-center gap-1.5 font-mono">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>SCIKIT-LEARN ADVISORY INFERENCE</span>
                    <span className="px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-500/40 text-[9px]">
                      {assessment.ml_advisory.model_status} BENCHMARK
                    </span>
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Confidence: {(assessment.ml_advisory.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  Advisory ML Model ({assessment.ml_advisory.primary_algorithm || 'LogisticRegression'}, {assessment.ml_advisory.model_version}) classified scenario features as{' '}
                  <span className="font-bold text-white font-mono">
                    {assessment.ml_advisory.ml_predicted_level}
                  </span>. Authoritative risk scoring is governed deterministically by formula R = 0.4H + 0.3E + 0.2V + 0.1D.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-500 font-mono text-xs">
            {assessmentError ? (
              <div className="text-rose-400">{assessmentError}</div>
            ) : (
              <div>COMPUTING AUTHORITATIVE RISK INTELLIGENCE...</div>
            )}
          </div>
        )}
      </div>

      {/* ===================================================================== */}
      {/* PRIORITIZED CIVIC RECOMMENDATIONS SECTION */}
      {/* ===================================================================== */}
      <div className="glass-panel rounded-xl p-6 sm:p-8 border border-navy-800 space-y-6 shadow-glow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-navy-800">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-brand-cyan" />
              <span>Prioritized Civic Response Recommendations</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Actionable operational directives calibrated to category risk and dominant formula drivers.
            </p>
          </div>

          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/40 border border-amber-500/30 text-[10px] font-mono text-amber-300">
            <span>STATUS: PROPOSED (DISPATCH PENDING)</span>
          </div>
        </div>

        {recommendations.length > 0 ? (
          <div className="space-y-4">
            {recommendations.map((rec, idx) => (
              <div
                key={rec.id || idx}
                className="p-4 rounded-xl bg-navy-900/40 border border-navy-800/80 hover:border-navy-700 transition-colors space-y-2.5"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    {getPriorityBadge(rec.priority)}
                    <h4 className="text-sm font-bold text-white">{rec.action}</h4>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-navy-950 text-slate-400 border border-navy-800 shrink-0">
                    STATUS: {rec.status}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  <span className="font-semibold text-slate-200">Rationale: </span>
                  {rec.rationale}
                </p>

                <div className="pt-2 border-t border-navy-800/60 flex flex-wrap items-center justify-between gap-3 text-[11px] font-mono">
                  <div className="flex items-center gap-1.5 text-brand-cyan">
                    <span>Suggested Next Action:</span>
                    <span className="text-slate-200 font-sans">{rec.suggested_next_step}</span>
                  </div>

                  {rec.responsible_department && (
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Building2 className="w-3.5 h-3.5 text-slate-500" />
                      <span>{rec.responsible_department}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-xs text-slate-500 font-mono">
            {loadingRecs ? 'LOADING RECOMMENDATIONS...' : 'NO CIVIC RECOMMENDATIONS PROPOSED FOR THIS RECORD.'}
          </div>
        )}
      </div>
    </div>
  );
};
