import React, { useState, useEffect, useCallback, useTransition } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  SlidersHorizontal,
  RotateCcw,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  Info,
  ArrowRight,
  Layers,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { simulateScenario, getIncidentById } from '../services/api';
import {
  RiskFactorInput,
  SimulationResponse,
  RiskLevel,
  Incident,
} from '../types';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export const SimulatorPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const incidentIdParam = searchParams.get('incident_id');
  const { token, role } = useAuth();
  const [, startTransition] = useTransition();

  // Linked incident reference
  const [linkedIncident, setLinkedIncident] = useState<Incident | null>(null);

  // Baseline Factor State
  const [baselineH, setBaselineH] = useState<number>(75);
  const [baselineE, setBaselineE] = useState<number>(70);
  const [baselineV, setBaselineV] = useState<number>(60);
  const [baselineD, setBaselineD] = useState<number>(50);

  // Simulated Factor State (Controlled by Sliders)
  const [simH, setSimH] = useState<number>(35);
  const [simE, setSimE] = useState<number>(40);
  const [simV, setSimV] = useState<number>(45);
  const [simD, setSimD] = useState<number>(30);

  const [scenarioName, setScenarioName] = useState<string>('Emergency Drainage & Traffic Mitigation');
  const [notes, setNotes] = useState<string>('Deploy mobile high-volume pumps and establish bus route diversions.');

  // Simulation API Results
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null);
  const [loadingSim, setLoadingSim] = useState<boolean>(false);
  const [simError, setSimError] = useState<string | null>(null);

  // Load linked incident if incident_id query param is present
  useEffect(() => {
    if (incidentIdParam && token) {
      getIncidentById(incidentIdParam, token)
        .then((inc) => {
          setLinkedIncident(inc);
          // Calibrate baseline based on severity
          const baseVal = inc.severity === 'HIGH' ? 80 : inc.severity === 'MEDIUM' ? 50 : 25;
          setBaselineH(baseVal);
          setBaselineE(Math.min(100, baseVal + 5));
          setBaselineV(Math.max(0, baseVal - 10));
          setBaselineD(Math.max(0, baseVal - 15));

          // Calibrate simulated targets
          setSimH(Math.max(10, baseVal - 40));
          setSimE(Math.max(10, baseVal - 30));
          setSimV(Math.max(10, baseVal - 20));
          setSimD(Math.max(10, baseVal - 20));

          setScenarioName(`Mitigation Scenario for ${inc.id}`);
        })
        .catch((err) => {
          console.warn('Could not load linked incident baseline:', err);
        });
    }
  }, [incidentIdParam, token]);

  // Execute Simulation via Backend API
  const runSimulation = useCallback(async () => {
    setLoadingSim(true);
    setSimError(null);

    const baselineFactors: RiskFactorInput = {
      hazard_severity: baselineH,
      exposure: baselineE,
      vulnerability: baselineV,
      duration: baselineD,
      source: 'USER_DIRECT',
    };

    const simulatedFactors: RiskFactorInput = {
      hazard_severity: simH,
      exposure: simE,
      vulnerability: simV,
      duration: simD,
      source: 'SIMULATION_OVERRIDE',
    };

    try {
      const res = await simulateScenario(
        {
          scenario_name: scenarioName || 'Civic Intervention Scenario',
          incident_id: linkedIncident ? linkedIncident.id : null,
          baseline_factors: baselineFactors,
          simulated_factors: simulatedFactors,
          intervention_notes: notes || undefined,
        },
        token
      );
      setSimulationResult(res);
    } catch (err: unknown) {
      setSimError(err instanceof Error ? err.message : 'Simulation evaluation failed.');
    } finally {
      setLoadingSim(false);
    }
  }, [baselineH, baselineE, baselineV, baselineD, simH, simE, simV, simD, scenarioName, notes, linkedIncident, token]);

  // Run simulation on mount and when slider inputs settle
  useEffect(() => {
    const timer = setTimeout(() => {
      startTransition(() => {
        runSimulation();
      });
    }, 300);
    return () => clearTimeout(timer);
  }, [runSimulation]);

  const handleResetToBaseline = () => {
    setSimH(baselineH);
    setSimE(baselineE);
    setSimV(baselineV);
    setSimD(baselineD);
  };

  const getLevelBadge = (level: RiskLevel) => {
    switch (level) {
      case 'HIGH':
        return <Badge variant="high" dot>HIGH (60–100)</Badge>;
      case 'MEDIUM':
        return <Badge variant="medium" dot>MEDIUM (30–59)</Badge>;
      case 'LOW':
        return <Badge variant="low" dot>LOW (0–29)</Badge>;
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-navy-800">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand-cyan/10 border border-brand-cyan/30 text-[11px] font-mono text-brand-cyan mb-2">
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>NON-DESTRUCTIVE CIVIC DECISION LAB</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            What-If Scenario Simulator
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Model potential civic interventions (water pumping, bus detours, concrete capping) to evaluate
            projected risk score reduction (ΔR) using the deterministic multi-criteria engine.
          </p>
        </div>

        {linkedIncident && (
          <div className="p-3.5 rounded-xl glass-panel border border-brand-cyan/30 flex items-center gap-3 shrink-0">
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-400 block">Baseline Incident</span>
              <span className="text-xs font-bold text-white block max-w-xs truncate">{linkedIncident.title}</span>
              <span className="text-[10px] font-mono text-brand-cyan">{linkedIncident.id}</span>
            </div>
            <Link to={`/incidents/${linkedIncident.id}`}>
              <Button variant="secondary" size="sm">
                <ExternalLink className="w-3.5 h-3.5" />
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Mandatory Non-Destructive Disclosure Notice */}
      <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-start gap-3 text-xs text-amber-200/90 leading-relaxed">
        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-amber-300 block">Hypothetical Scenario Transparency Notice:</span>
          Simulations are evaluated in-memory and flagged as{' '}
          <span className="font-mono text-amber-300">SIMULATION_OVERRIDE (is_simulation=true)</span>.
          They do not overwrite or modify live incident records in Cloud Firestore. A simulated improvement
          does not claim verified physical mitigation until response crews confirm on-site resolution.
        </div>
      </div>

      {/* Main Two-Column Work Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Sliders & Scenario Controls (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="glass-panel rounded-xl p-6 border border-navy-800 space-y-6 shadow-glow-card">
            <div className="flex items-center justify-between pb-4 border-b border-navy-800">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-brand-cyan" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                  Intervention Parameter Tuning
                </h3>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleResetToBaseline}
                className="text-xs text-slate-400 hover:text-white"
              >
                <RotateCcw className="w-3.5 h-3.5 mr-1" />
                Reset to Baseline
              </Button>
            </div>

            {/* Scenario Metadata Inputs */}
            <div className="space-y-3">
              <div>
                <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                  Scenario Title
                </label>
                <input
                  type="text"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950/80 border border-navy-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-brand-cyan font-mono"
                  placeholder="e.g. Dewatering Pump Deployment & Bus Detour"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                  Intervention Description / Field Notes
                </label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950/80 border border-navy-800 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-brand-cyan"
                  placeholder="Detail planned civic response actions..."
                />
              </div>
            </div>

            {/* Four Sliders */}
            <div className="space-y-6 pt-2">
              {/* 1. Hazard Severity Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Hazard Severity (H) — <span className="font-mono text-brand-cyan">40% Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineH}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">{simH} / 100</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={simH}
                  onChange={(e) => setSimH(Number(e.target.value))}
                  className="w-full accent-brand-cyan cursor-pointer h-2 bg-navy-950 rounded-lg"
                />
                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>0 (Negligible / De-energized)</span>
                  <span>50 (Moderate)</span>
                  <span>100 (Critical Catastrophe)</span>
                </div>
              </div>

              {/* 2. Exposure Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Population Exposure (E) — <span className="font-mono text-brand-cyan">30% Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineE}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">{simE} / 100</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={simE}
                  onChange={(e) => setSimE(Number(e.target.value))}
                  className="w-full accent-brand-cyan cursor-pointer h-2 bg-navy-950 rounded-lg"
                />
                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>0 (Evacuated / Barricaded)</span>
                  <span>50 (Standard Residential)</span>
                  <span>100 (Dense Transit Hub)</span>
                </div>
              </div>

              {/* 3. Vulnerability Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Infrastructure Vulnerability (V) — <span className="font-mono text-brand-cyan">20% Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineV}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">{simV} / 100</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={simV}
                  onChange={(e) => setSimV(Number(e.target.value))}
                  className="w-full accent-brand-cyan cursor-pointer h-2 bg-navy-950 rounded-lg"
                />
                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>0 (Reinforced / High Resilience)</span>
                  <span>50 (Moderate Fragility)</span>
                  <span>100 (Unprotected / Frail)</span>
                </div>
              </div>

              {/* 4. Duration Slider */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Unresolved Duration (D) — <span className="font-mono text-brand-cyan">10% Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineD}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">{simD} / 100</span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="1"
                  value={simD}
                  onChange={(e) => setSimD(Number(e.target.value))}
                  className="w-full accent-brand-cyan cursor-pointer h-2 bg-navy-950 rounded-lg"
                />
                <div className="flex justify-between text-[10px] font-mono text-slate-500">
                  <span>0 (&lt; 1 Hour / Rapid Fix)</span>
                  <span>50 (24–48 Hours)</span>
                  <span>100 (Prolonged Inaction)</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Comparative Results & Delta Impact (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-panel rounded-xl p-6 border border-navy-800 space-y-6 shadow-glow-card">
            <div className="flex items-center justify-between pb-4 border-b border-navy-800">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-cyan" />
                <span>Projected Delta Analysis</span>
              </h3>
              {loadingSim && (
                <div className="w-4 h-4 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
              )}
            </div>

            {simError && (
              <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-800/40 text-xs text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{simError}</span>
              </div>
            )}

            {simulationResult ? (
              <div className="space-y-6">
                {/* Score Comparison Display */}
                <div className="grid grid-cols-2 gap-4">
                  {/* Baseline Box */}
                  <div className="p-4 rounded-xl bg-navy-950/60 border border-navy-800 text-center space-y-1.5">
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                      Baseline State
                    </span>
                    <div className="text-3xl font-extrabold text-white font-mono">
                      {simulationResult.baseline_score.toFixed(1)}
                    </div>
                    <div>{getLevelBadge(simulationResult.baseline_level)}</div>
                  </div>

                  {/* Simulated Box */}
                  <div className="p-4 rounded-xl bg-navy-900/60 border border-brand-cyan/40 text-center space-y-1.5 shadow-glow-card">
                    <span className="text-[10px] font-mono text-brand-cyan uppercase tracking-wider block">
                      Simulated State
                    </span>
                    <div className="text-3xl font-extrabold text-brand-cyan font-mono">
                      {simulationResult.simulated_score.toFixed(1)}
                    </div>
                    <div>{getLevelBadge(simulationResult.simulated_level)}</div>
                  </div>
                </div>

                {/* Score Difference Indicator */}
                <div
                  className={`p-4 rounded-xl border flex items-center justify-between ${
                    simulationResult.score_difference < 0
                      ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                      : simulationResult.score_difference > 0
                      ? 'bg-rose-950/20 border-rose-500/40 text-rose-300'
                      : 'bg-slate-900/40 border-slate-700/40 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {simulationResult.score_difference < 0 ? (
                      <TrendingDown className="w-5 h-5 text-emerald-400" />
                    ) : simulationResult.score_difference > 0 ? (
                      <TrendingUp className="w-5 h-5 text-rose-400" />
                    ) : (
                      <CheckCircle2 className="w-5 h-5 text-slate-400" />
                    )}
                    <div>
                      <span className="text-xs font-bold block">
                        {simulationResult.score_difference < 0
                          ? 'Net Risk Reduction (Mitigation)'
                          : simulationResult.score_difference > 0
                          ? 'Net Risk Escalation (Deterioration)'
                          : 'Neutral Scenario (Zero Net Shift)'}
                      </span>
                      <span className="text-[10px] font-mono opacity-80">
                        Formula: R = 0.4H + 0.3E + 0.2V + 0.1D
                      </span>
                    </div>
                  </div>

                  <div className="text-xl font-bold font-mono">
                    {simulationResult.score_difference > 0 ? '+' : ''}
                    {simulationResult.score_difference.toFixed(1)} pts
                  </div>
                </div>

                {/* Level Transition Alert */}
                {simulationResult.level_changed && (
                  <div className="p-3.5 rounded-xl bg-brand-cyan/10 border border-brand-cyan/30 text-xs text-brand-cyan flex items-center justify-between">
                    <span className="font-semibold flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4" />
                      Classification Transition:
                    </span>
                    <span className="font-mono font-bold">
                      {simulationResult.baseline_level} → {simulationResult.simulated_level}
                    </span>
                  </div>
                )}

                {/* Primary Driver of Change */}
                <div className="p-4 rounded-xl bg-navy-950/60 border border-navy-800 space-y-1.5">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                    Key Driver Attribution
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed font-medium">
                    {simulationResult.primary_mitigation_driver}
                  </p>
                </div>

                {/* Shift Details Breakdown */}
                <div className="space-y-2">
                  <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                    Parameter Shift Summary
                  </span>
                  <ul className="space-y-1.5">
                    {simulationResult.factors_responsible.map((shift, idx) => (
                      <li
                        key={idx}
                        className="text-xs font-mono text-slate-300 p-2 rounded bg-navy-950/40 border border-navy-800/60"
                      >
                        {shift}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 space-y-2 text-slate-500 font-mono text-xs">
                <div className="w-6 h-6 rounded-full border-2 border-slate-700 border-t-transparent animate-spin mx-auto" />
                <p>EVALUATING HYPOTHETICAL PARAMETERS...</p>
              </div>
            )}
            {/* Multi-Scenario Municipal Planning Link for Analysts/Admins */}
            {(role === 'ANALYST' || role === 'ADMIN') && (
              <div className="pt-4 border-t border-navy-800">
                <Link
                  to={linkedIncident ? `/mitigation-planner?incident_id=${linkedIncident.id}` : '/mitigation-planner'}
                  className="flex items-center justify-between p-3.5 rounded-xl bg-navy-950/70 border border-brand-cyan/30 hover:border-brand-cyan transition-all group"
                >
                  <div className="flex items-center gap-2.5">
                    <Layers className="w-4 h-4 text-brand-cyan group-hover:scale-110 transition-transform" />
                    <div>
                      <span className="text-xs font-bold text-white block">
                        Launch Municipal Mitigation Planner
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Evaluate 2–5 competing scenarios & generate briefs
                      </span>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-brand-cyan group-hover:translate-x-1 transition-transform" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
