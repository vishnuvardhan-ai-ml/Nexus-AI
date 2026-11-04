import React from 'react';
import { Link } from 'react-router-dom';
import {
  Shield,
  ArrowRight,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
  Cpu,
  BarChart2,
  Sliders,
  CheckCircle2,
  Lock,
  Layers,
  ChevronRight,
  Activity,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { HealthStatusWidget } from '../components/ui/HealthStatusWidget';

export const LandingPage: React.FC = () => {
  const workflowSteps = [
    {
      num: '01',
      step: 'REPORT',
      title: 'Community Ingestion',
      desc: 'Residents and sensors submit real-time geo-tagged incident reports with multimodal details.',
      icon: Layers,
    },
    {
      num: '02',
      step: 'ANALYZE',
      title: 'ML Classification',
      desc: 'TF-IDF vectorizer and logistic classification automatically identify category and key hazard entities.',
      icon: Cpu,
    },
    {
      num: '03',
      step: 'PREDICT',
      title: 'Risk Computation',
      desc: 'Deterministic multi-factor risk model computes baseline score based on hazard intensity, exposure, and duration.',
      icon: Activity,
    },
    {
      num: '04',
      step: 'EXPLAIN',
      title: 'Factor Breakdown',
      desc: 'Transparent weights and explainable contribution percentages remove AI black-box ambiguity.',
      icon: BarChart2,
    },
    {
      num: '05',
      step: 'SIMULATE',
      title: 'What-If Engine',
      desc: 'Decision-makers simulate interventions (e.g., pumps, barricades, routing) to preview risk mitigation.',
      icon: Sliders,
    },
    {
      num: '06',
      step: 'RECOMMEND',
      title: 'Action Dispatch',
      desc: 'Optimized actionable playbooks generate priority work-orders and emergency civic advisories.',
      icon: CheckCircle2,
    },
  ];

  const categories = [
    {
      title: 'Waterlogging',
      icon: Droplets,
      color: 'from-cyan-500/20 to-blue-600/20 text-cyan-400 border-cyan-500/30',
      desc: 'Monsoon flooding, blocked arterial storm drains, and urban submerged thoroughfares.',
    },
    {
      title: 'Road Damage',
      icon: Construction,
      color: 'from-amber-500/20 to-orange-600/20 text-amber-400 border-amber-500/30',
      desc: 'Severe potholes, pavement subsidence, cave-ins, and bridge joint compromises.',
    },
    {
      title: 'Electrical Hazards',
      icon: Zap,
      color: 'from-yellow-500/20 to-amber-600/20 text-yellow-400 border-yellow-500/30',
      desc: 'Downed powerlines, exposed junction boxes, transformer fires, and water-contact short circuits.',
    },
    {
      title: 'Waste Management',
      icon: Trash2,
      color: 'from-emerald-500/20 to-teal-600/20 text-emerald-400 border-emerald-500/30',
      desc: 'Toxic garbage dumping, biohazard accumulation, drain-choking plastics, and leachate runoff.',
    },
    {
      title: 'Extreme Heat',
      icon: Flame,
      color: 'from-rose-500/20 to-red-600/20 text-rose-400 border-rose-500/30',
      desc: 'Urban heat island spikes, critical wet-bulb alerts, water scarcity spots, and grid overload.',
    },
  ];

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 flex flex-col bg-grid-pattern">
      {/* Top Navigation Banner */}
      <header className="border-b border-navy-800/80 bg-navy-950/80 backdrop-blur-md sticky top-0 z-50 px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-cyan/20 border border-brand-cyan/40 flex items-center justify-center text-brand-cyan shadow-glow-cyan">
            <Shield className="w-4 h-4" />
          </div>
          <span className="font-bold text-lg tracking-wider text-white">
            NEXUS<span className="text-brand-cyan font-mono ml-0.5">AI</span>
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link
            to="/dashboard"
            className="text-xs font-semibold px-4 py-2 rounded-lg bg-gradient-to-r from-brand-cyan to-brand-blue text-navy-950 hover:brightness-110 transition-all shadow-glow-cyan flex items-center gap-1.5"
          >
            <span>Launch Dashboard</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative px-4 sm:px-8 py-20 lg:py-28 max-w-7xl mx-auto w-full text-center flex flex-col items-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-navy-900 border border-brand-cyan/30 text-brand-cyan text-xs font-mono font-medium mb-6 shadow-glow-cyan">
          <span className="w-2 h-2 rounded-full bg-brand-cyan animate-pulse" />
          COMMUNITY INTELLIGENCE & RISK DECISION PLATFORM
        </div>

        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight max-w-5xl leading-tight">
          Turning Civic Incidents Into{' '}
          <span className="bg-gradient-to-r from-brand-cyan via-sky-300 to-brand-blue bg-clip-text text-transparent">
            Explainable Risk Decisions
          </span>
        </h1>

        <p className="mt-6 text-base sm:text-xl text-slate-300 max-w-3xl leading-relaxed font-normal">
          An end-to-end intelligence platform that converts raw community incident reports into structured
          classifications, deterministic multi-factor risk scores, and what-if scenario simulations for civic leaders.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link to="/dashboard">
            <Button size="lg" className="px-8 shadow-glow-cyan">
              <span>Open Intelligence Console</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>

          <a href="#equation">
            <Button variant="secondary" size="lg" className="px-6">
              <span>Inspect Risk Equation</span>
            </Button>
          </a>
        </div>

        {/* Live Backend Telemetry Integration */}
        <div className="mt-12 w-full max-w-3xl text-left" id="telemetry">
          <HealthStatusWidget />
        </div>
      </section>

      {/* 6-Step Workflow Section */}
      <section className="px-4 sm:px-8 py-20 max-w-7xl mx-auto w-full border-t border-navy-800/80" id="workflow">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <Badge variant="cyan" dot className="mb-3">
            DECISION ARCHITECTURE
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            From Raw Citizen Report to Actionable Civic Playbook
          </h2>
          <p className="mt-3 text-slate-400 text-sm sm:text-base">
            Structured 6-phase pipeline designed to eliminate decision latency and provide total explainability.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {workflowSteps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.step}
                className="glass-panel glass-panel-hover rounded-xl p-6 relative border border-navy-800"
              >
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono font-bold text-brand-cyan bg-brand-cyan/10 px-2.5 py-1 rounded border border-brand-cyan/20">
                    PHASE {step.num}
                  </span>
                  <div className="p-2 rounded-lg bg-navy-900 border border-navy-700/60 text-slate-300">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>

                <h3 className="text-base font-bold text-white tracking-wide">{step.title}</h3>
                <p className="text-xs font-mono text-brand-sky mt-0.5 tracking-wider font-semibold">
                  [{step.step}]
                </p>
                <p className="text-xs text-slate-400 mt-2.5 leading-relaxed">{step.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Transparent Risk Engine Section */}
      <section className="px-4 sm:px-8 py-20 max-w-7xl mx-auto w-full border-t border-navy-800/80" id="equation">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-6 space-y-4">
            <Badge variant="cyan" dot>
              TRANSPARENT RISK ENGINE
            </Badge>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
              Mathematical Transparency Over Opaque AI Guesswork
            </h2>
            <p className="text-slate-300 text-sm leading-relaxed">
              Unlike black-box models that cannot explain emergency recommendations to municipal stakeholders,
              NEXUS AI computes risk using a verified, weighted multi-factor equation where every input factor is on a normalized 0–100 scale:
            </p>

            <div className="p-5 rounded-xl bg-navy-900/90 border border-brand-cyan/30 shadow-glow-cyan font-mono text-center">
              <span className="text-xs text-slate-400 block mb-1 uppercase tracking-widest">
                CIVIC RISK FORMULATION
              </span>
              <div className="text-xl sm:text-2xl font-bold text-brand-cyan tracking-wider">
                Risk = 0.4H + 0.3E + 0.2V + 0.1D
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 pt-2 text-xs">
              <div className="p-3 rounded-lg bg-navy-900/60 border border-navy-800">
                <span className="font-bold text-brand-cyan font-mono">H (40%)</span>
                <p className="text-slate-400 mt-0.5">Hazard intensity & physical magnitude.</p>
              </div>
              <div className="p-3 rounded-lg bg-navy-900/60 border border-navy-800">
                <span className="font-bold text-brand-sky font-mono">E (30%)</span>
                <p className="text-slate-400 mt-0.5">Population & critical asset exposure.</p>
              </div>
              <div className="p-3 rounded-lg bg-navy-900/60 border border-navy-800">
                <span className="font-bold text-amber-400 font-mono">V (20%)</span>
                <p className="text-slate-400 mt-0.5">Structural & demographic vulnerability.</p>
              </div>
              <div className="p-3 rounded-lg bg-navy-900/60 border border-navy-800">
                <span className="font-bold text-slate-300 font-mono">D (10%)</span>
                <p className="text-slate-400 mt-0.5">Active or projected event duration.</p>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6 space-y-4">
            <div className="glass-panel rounded-xl p-6 border border-navy-800">
              <h4 className="text-sm font-semibold text-white uppercase tracking-wider font-mono mb-4 flex items-center justify-between">
                <span>Verified Severity Thresholds</span>
                <span className="text-xs text-slate-400 font-normal">Scale: 0 – 100</span>
              </h4>

              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/30 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-emerald-400">0 – 29 SCORE</span>
                    <h5 className="text-sm font-bold text-white mt-0.5">LOW RISK</h5>
                    <p className="text-xs text-slate-400">Routine municipal queue; standard logging.</p>
                  </div>
                  <Badge variant="low" dot>
                    MONITORING
                  </Badge>
                </div>

                <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-500/30 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-amber-400">30 – 59 SCORE</span>
                    <h5 className="text-sm font-bold text-white mt-0.5">MEDIUM RISK</h5>
                    <p className="text-xs text-slate-400">Dispatched patrol inspection; preventative action.</p>
                  </div>
                  <Badge variant="medium" dot>
                    ELEVATED
                  </Badge>
                </div>

                <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-500/30 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-rose-400">60 – 100 SCORE</span>
                    <h5 className="text-sm font-bold text-white mt-0.5">HIGH RISK</h5>
                    <p className="text-xs text-slate-400">Emergency response mobilization; civic alert broadcast.</p>
                  </div>
                  <Badge variant="high" dot>
                    CRITICAL
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Incident Categories */}
      <section className="px-4 sm:px-8 py-20 max-w-7xl mx-auto w-full border-t border-navy-800/80" id="categories">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <Badge variant="cyan" dot className="mb-3">
            CIVIC TAXONOMY
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-white">
            5 Core Urban Hazard Categories
          </h2>
          <p className="mt-3 text-slate-400 text-sm sm:text-base">
            Trained with lightweight TF-IDF & Logistic Regression classifiers to handle high-frequency community reports.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((cat) => {
            const Icon = cat.icon;
            return (
              <div key={cat.title} className="glass-panel glass-panel-hover rounded-xl p-6 border border-navy-800">
                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${cat.color} border flex items-center justify-center mb-4`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-bold text-white">{cat.title}</h3>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{cat.desc}</p>
              </div>
            );
          })}

          <div className="glass-panel rounded-xl p-6 border border-dashed border-brand-cyan/30 flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-lg bg-brand-cyan/10 border border-brand-cyan/30 flex items-center justify-center text-brand-cyan mb-4">
                <Lock className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-white">RBAC Protected</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                Roles for <span className="text-slate-200 font-mono">COMMUNITY_USER</span>, <span className="text-slate-200 font-mono">ANALYST</span>, and <span className="text-slate-200 font-mono">ADMIN</span> verified via secure claims.
              </p>
            </div>
            <Link to="/dashboard" className="mt-4">
              <Button variant="outline" size="sm" className="w-full">
                Enter Console
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-navy-800/80 bg-navy-950 py-10 px-4 sm:px-8 mt-auto">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-brand-cyan" />
            <span className="font-semibold text-slate-300">NEXUS AI</span>
            <span>— Community Intelligence & Risk Decision Platform</span>
          </div>
          <div className="flex items-center gap-6 font-mono text-[11px]">
            <span>FastAPI + Vite React TS</span>
            <span>Transparent Risk Equation</span>
            <span>Milestone 1 Verified</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
