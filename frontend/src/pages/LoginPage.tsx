import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Shield, Lock, Mail, ArrowRight, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { UserRole } from '../types';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { login, quickDevLogin, error, clearError, isFirebaseActive, firebaseProjectId } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : 'Invalid credentials or login failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDevRoleLogin = async (targetRole: UserRole) => {
    setLocalError(null);
    clearError();
    setIsSubmitting(true);
    try {
      await quickDevLogin(targetRole);
      navigate(from, { replace: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan shadow-glow-cyan mb-2">
            <Shield className="w-6 h-6" />
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            Sign In to NEXUS<span className="text-brand-cyan font-mono ml-0.5">AI</span>
          </h2>
          <p className="text-xs text-slate-400">
            Civic incident intelligence, risk assessment, and decision telemetry.
          </p>
        </div>

        {/* Login Card */}
        <div className="glass-panel rounded-xl p-7 border border-navy-800 shadow-glow-card">
          {/* Live Firebase Auth Mode Indicator */}
          {isFirebaseActive ? (
            <div className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-navy-900/90 border border-brand-cyan/20 text-[11px] font-mono mb-5">
              <span className="flex items-center gap-1.5 text-brand-cyan font-medium">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-cyan opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-cyan"></span>
                </span>
                LIVE FIREBASE AUTH
              </span>
              <span className="text-slate-400 font-mono text-[10px]">
                {firebaseProjectId || 'nexus-ai-4a631'}
              </span>
            </div>
          ) : (
            <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-amber-950/40 border border-amber-800/40 text-[11px] text-amber-300 mb-5">
              <span className="flex items-center gap-1.5 font-semibold">
                <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                FIREBASE STANDBY
              </span>
              <span className="text-[10px] text-amber-400/80">Offline Dev Mode</span>
            </div>
          )}

          {(localError || error) && (
            <div className="mb-5 p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-rose-200">Authentication Failed</p>
                <p className="mt-0.5 text-rose-300/90">{localError || error}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-slate-300 mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="resident@community.gov"
                  className="w-full pl-9 pr-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                  required
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-2"
              isLoading={isSubmitting}
            >
              <span>Authenticate & Enter Console</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </form>

          {/* Quick Evaluator / Demo Role Access */}
          <div className="mt-6 pt-5 border-t border-navy-800">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 text-brand-cyan" />
                Evaluator RBAC Test Roles:
              </span>
              <span className="text-[10px] text-brand-cyan font-mono">1-CLICK LOGIN</span>
            </div>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleDevRoleLogin('COMMUNITY_USER')}
                disabled={isSubmitting}
                className="px-2 py-2 rounded-lg bg-navy-900 hover:bg-navy-800 border border-navy-700 hover:border-brand-cyan/40 text-slate-200 text-xs font-mono transition-all text-center group"
              >
                <div className="font-semibold text-[11px] text-brand-sky group-hover:text-brand-cyan">
                  COMMUNITY
                </div>
                <div className="text-[10px] text-slate-400">Reporter</div>
              </button>

              <button
                type="button"
                onClick={() => handleDevRoleLogin('ANALYST')}
                disabled={isSubmitting}
                className="px-2 py-2 rounded-lg bg-navy-900 hover:bg-navy-800 border border-navy-700 hover:border-amber-400/40 text-slate-200 text-xs font-mono transition-all text-center group"
              >
                <div className="font-semibold text-[11px] text-amber-400 group-hover:text-amber-300">
                  ANALYST
                </div>
                <div className="text-[10px] text-slate-400">Triage & Sim</div>
              </button>

              <button
                type="button"
                onClick={() => handleDevRoleLogin('ADMIN')}
                disabled={isSubmitting}
                className="px-2 py-2 rounded-lg bg-navy-900 hover:bg-navy-800 border border-navy-700 hover:border-rose-400/40 text-slate-200 text-xs font-mono transition-all text-center group"
              >
                <div className="font-semibold text-[11px] text-rose-400 group-hover:text-rose-300">
                  ADMIN
                </div>
                <div className="text-[10px] text-slate-400">Full Access</div>
              </button>
            </div>
          </div>
        </div>

        {/* Footer Link */}
        <p className="text-center text-xs text-slate-400">
          New community member?{' '}
          <Link to="/register" className="text-brand-cyan hover:underline font-medium">
            Create civic account
          </Link>
        </p>
      </div>
    </div>
  );
};
