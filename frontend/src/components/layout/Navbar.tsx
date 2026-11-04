import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, User, Menu, X, ArrowUpRight, LogOut, LogIn, Plus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { HealthStatusWidget } from '../ui/HealthStatusWidget';
import { Badge } from '../ui/Badge';

interface NavbarProps {
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar, isSidebarOpen }) => {
  const location = useLocation();
  const isLanding = location.pathname === '/';
  const { user, role, logout } = useAuth();

  const getRoleBadgeVariant = (r: string) => {
    switch (r) {
      case 'ADMIN':
        return 'high';
      case 'ANALYST':
        return 'medium';
      default:
        return 'cyan';
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-navy-800/80 bg-navy-950/80 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand identity */}
        <div className="flex items-center gap-3">
          {!isLanding && (
            <button
              onClick={onToggleSidebar}
              className="p-2 -ml-2 text-slate-400 hover:text-white md:hidden"
              aria-label="Toggle navigation drawer"
            >
              {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          )}

          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-brand-cyan/20 to-brand-blue/30 border border-brand-cyan/40 shadow-glow-cyan group-hover:border-brand-cyan transition-all">
              <Shield className="w-5 h-5 text-brand-cyan" />
              <div className="absolute inset-0 rounded-xl bg-brand-cyan/10 animate-pulse pointer-events-none" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold tracking-wider text-base sm:text-lg bg-gradient-to-r from-white via-slate-200 to-brand-cyan bg-clip-text text-transparent">
                NEXUS<span className="text-brand-cyan font-mono ml-1 font-extrabold">AI</span>
              </span>
              <span className="text-[10px] tracking-widest text-slate-400 uppercase font-mono hidden sm:inline">
                Community Intelligence Platform
              </span>
            </div>
          </Link>
        </div>

        {/* Global Navigation links for Landing */}
        {isLanding ? (
          <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
            <a href="#workflow" className="text-slate-300 hover:text-brand-cyan transition-colors">
              Workflow
            </a>
            <a href="#categories" className="text-slate-300 hover:text-brand-cyan transition-colors">
              Risk Taxonomy
            </a>
            <a href="#equation" className="text-slate-300 hover:text-brand-cyan transition-colors">
              Risk Equation
            </a>
            <a href="#telemetry" className="text-slate-300 hover:text-brand-cyan transition-colors">
              Telemetry
            </a>
          </nav>
        ) : null}

        {/* Actions & Health Telemetry status */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="hidden sm:block">
            <HealthStatusWidget compact />
          </div>

          {isLanding ? (
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-brand-cyan/10 hover:bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40 hover:border-brand-cyan transition-all shadow-glow-cyan"
            >
              <span>Live Console</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          ) : user ? (
            <div className="flex items-center gap-2 pl-2 border-l border-navy-800">
              <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-navy-900 border border-navy-800 text-xs">
                <span className="font-mono text-slate-300 text-[11px] hidden md:inline truncate max-w-[120px]">
                  {user.email.split('@')[0]}
                </span>
                <Badge variant={getRoleBadgeVariant(role)} dot className="text-[10px] py-0 px-2">
                  {role}
                </Badge>
              </div>

              <button
                onClick={() => logout()}
                className="p-1.5 rounded-lg bg-navy-900 hover:bg-navy-800 border border-navy-800 text-slate-400 hover:text-rose-400 transition-colors"
                title="Sign Out"
                aria-label="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-brand-cyan/10 hover:bg-brand-cyan/20 text-brand-cyan border border-brand-cyan/40 transition-all"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
