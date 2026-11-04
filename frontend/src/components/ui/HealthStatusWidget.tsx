import React, { useEffect, useState, useCallback } from 'react';
import { Activity, RefreshCw, Server, Cpu, Database, CheckCircle2, AlertCircle } from 'lucide-react';
import { getSystemHealth } from '../../services/api';
import { SystemHealthResponse } from '../../types';
import { Badge } from './Badge';

export const HealthStatusWidget: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<string>('');

  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await getSystemHealth();
      const duration = Math.round(performance.now() - start);
      setLatency(duration);
      setHealth(data);
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      const duration = Math.round(performance.now() - start);
      setLatency(duration);
      setError(err instanceof Error ? err.message : 'Backend unreachable');
      setHealth(null);
      setLastChecked(new Date().toLocaleTimeString());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div
          className={`w-2.5 h-2.5 rounded-full ${
            loading
              ? 'bg-amber-400 animate-ping'
              : health?.status === 'healthy'
              ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
              : 'bg-rose-500 shadow-[0_0_8px_#f43f5e]'
          }`}
          title={health ? `API Online (${latency}ms)` : 'API Offline'}
        />
        <span className="text-xs font-mono text-slate-300 hidden sm:inline">
          {loading ? 'CHECKING...' : health ? `ONLINE (${latency}ms)` : 'OFFLINE'}
        </span>
        <button
          onClick={checkHealth}
          disabled={loading}
          aria-label="Refresh telemetry status"
          className="text-slate-400 hover:text-brand-cyan transition-colors p-1"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin text-brand-cyan' : ''}`} />
        </button>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-xl p-5 border border-brand-cyan/20 relative overflow-hidden">
      <div className="flex items-center justify-between pb-3 border-b border-navy-700/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white tracking-wide">Telemetry & Backend Verification</h4>
            <p className="text-xs text-slate-400 font-mono">
              Endpoint: /api/v1/health {lastChecked ? `· Checked at ${lastChecked}` : ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {health?.status === 'healthy' ? (
            <Badge variant="low" dot>
              OPERATIONAL ({latency}ms)
            </Badge>
          ) : error ? (
            <Badge variant="high" dot>
              DISCONNECTED
            </Badge>
          ) : (
            <Badge variant="medium" dot>
              PROBING...
            </Badge>
          )}

          <button
            onClick={checkHealth}
            disabled={loading}
            className="p-1.5 rounded-lg bg-navy-800 hover:bg-navy-700 border border-navy-700 text-slate-300 hover:text-brand-cyan transition-all"
            title="Refresh Health Probe"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-brand-cyan' : ''}`} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="mt-4 p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-semibold text-rose-300">FastAPI Backend Standby</p>
            <p className="text-rose-400/80 mt-0.5">{error}</p>
            <p className="text-slate-400 mt-1 font-mono text-[11px]">
              Tip: Start the backend with: <code className="text-brand-cyan">cd backend && uvicorn app.main:app --reload</code>
            </p>
          </div>
        </div>
      ) : health ? (
        <div className="mt-4 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-2.5 rounded-lg bg-navy-900/60 border border-navy-700/50 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <Cpu className="w-3.5 h-3.5 text-brand-cyan" />
                <span>Classifier Engine</span>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 uppercase font-semibold">
                {health.subsystems.classifier}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-navy-900/60 border border-navy-700/50 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <Activity className="w-3.5 h-3.5 text-brand-sky" />
                <span>Risk Equation</span>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 uppercase font-semibold">
                {health.subsystems.risk_engine}
              </span>
            </div>

            <div className="p-2.5 rounded-lg bg-navy-900/60 border border-navy-700/50 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-slate-300">
                <Database className="w-3.5 h-3.5 text-amber-400" />
                <span>Cloud Firestore</span>
              </div>
              <span className="text-[11px] font-mono text-amber-400 uppercase font-semibold">
                {health.subsystems.database}
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 font-mono pt-1">
            <span className="flex items-center gap-1.5">
              <Server className="w-3 h-3 text-slate-500" />
              Service: <span className="text-slate-200">{health.service}</span>
            </span>
            <span>Version: <span className="text-brand-cyan">{health.version}</span></span>
            <span>Env: <span className="text-slate-200">{health.environment}</span></span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
