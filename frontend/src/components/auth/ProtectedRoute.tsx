import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { user, loading, role } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
        <div className="w-8 h-8 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
        <p className="text-xs font-mono text-slate-400">VERIFYING AUTHENTICATION & RBAC CLAIMS...</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(role)) {
    return (
      <div className="max-w-md mx-auto my-12 p-6 glass-panel rounded-xl border border-rose-500/30 text-center">
        <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto mb-4">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-bold text-white">Access Restricted</h3>
        <p className="text-xs text-slate-400 mt-2 leading-relaxed">
          This operation requires verified authorization claims for:{' '}
          <span className="font-mono text-slate-200">{allowedRoles.join(', ')}</span>.
          Your current verified role is <span className="font-mono text-brand-cyan">{role}</span>.
        </p>
        <div className="mt-6">
          <Button variant="secondary" size="sm" onClick={() => window.history.back()}>
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
