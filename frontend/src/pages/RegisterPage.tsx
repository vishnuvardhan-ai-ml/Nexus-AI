import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, Lock, Mail, User, ArrowRight, AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';

export const RegisterPage: React.FC = () => {
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, error, clearError, isFirebaseActive, firebaseProjectId } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!isFirebaseActive) {
      setLocalError(
        'Cannot register: Live Firebase Authentication is not connected. Please ensure valid VITE_FIREBASE_* variables are saved in frontend/.env and restart the Vite server.'
      );
      return;
    }

    if (!displayName.trim()) {
      setLocalError('Please enter your civic display name.');
      return;
    }
    if (!email.trim()) {
      setLocalError('Please provide a valid email address.');
      return;
    }
    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email, password, displayName);
      navigate('/dashboard', { replace: true });
    } catch (err: unknown) {
      setLocalError(err instanceof Error ? err.message : 'Registration failed.');
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
            Register for NEXUS<span className="text-brand-cyan font-mono ml-0.5">AI</span>
          </h2>
          <p className="text-xs text-slate-400">
            Join the decentralized community hazard reporting and risk intelligence network.
          </p>
        </div>

        {/* Register Card */}
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
              <span className="text-[10px] text-amber-400/80">Restart Vite with .env</span>
            </div>
          )}

          {(localError || error) && (
            <div className="mb-5 p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-rose-200">Registration Error</p>
                <p className="mt-0.5 text-rose-300/90">{localError || error}</p>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-slate-300 mb-1.5">
                Display Name
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Civic Reporter Name"
                  className="w-full pl-9 pr-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                  required
                />
              </div>
            </div>

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
                  placeholder="Min. 6 characters"
                  className="w-full pl-9 pr-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono uppercase tracking-wider text-slate-300 mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  className="w-full pl-9 pr-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                  required
                />
              </div>
            </div>

            {/* RBAC Security Notice */}
            <div className="p-3 rounded-lg bg-navy-900/80 border border-navy-700/60 text-slate-300 text-[11px] leading-relaxed flex items-start gap-2.5">
              <ShieldCheck className="w-4 h-4 text-brand-cyan shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Strict RBAC Policy: </span>
                Self-registered accounts automatically receive verified{' '}
                <span className="font-mono text-brand-cyan font-semibold">COMMUNITY_USER</span> privileges.
                Analyst or Admin access requires trusted backend claim assignment.
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-2"
              isLoading={isSubmitting}
            >
              <span>Create Account & Verify</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </form>
        </div>

        {/* Footer Link */}
        <p className="text-center text-xs text-slate-400">
          Already registered?{' '}
          <Link to="/login" className="text-brand-cyan hover:underline font-medium">
            Sign in here
          </Link>
        </p>
      </div>
    </div>
  );
};
