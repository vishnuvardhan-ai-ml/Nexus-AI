import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertTriangle,
  PlusCircle,
  BrainCircuit,
  MapPin,
  SlidersHorizontal,
  Layers,
  BarChart3,
  CheckSquare,
  Settings,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
  ShieldCheck,
  UserCheck,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/Badge';

interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user, role } = useAuth();

  const primaryNavItems = [
    { label: 'Overview', to: '/dashboard', icon: LayoutDashboard },
    { label: 'Incident Registry', to: '/incidents', icon: AlertTriangle },
    { label: 'Report Incident', to: '/incidents/new', icon: PlusCircle },
    { label: 'AI Intelligence', to: '/intelligence', icon: BrainCircuit },
    { label: 'Interactive Risk Map', to: '/map', icon: MapPin },
    { label: 'What-If Simulator', to: '/simulator', icon: SlidersHorizontal },
    { label: 'Mitigation Planner', to: '/mitigation-planner', icon: Layers },
    { label: 'Analytics', to: '/analytics', icon: BarChart3 },
    { label: 'Action Center', to: '/actions', icon: CheckSquare },
    { label: 'Settings & Admin', to: '/settings', icon: Settings },
  ];

  const categories = [
    { label: 'Waterlogging', icon: Droplets, color: 'text-sky-400', to: '/incidents?category=waterlogging' },
    { label: 'Road Damage', icon: Construction, color: 'text-amber-400', to: '/incidents?category=road_damage' },
    { label: 'Electrical Hazard', icon: Zap, color: 'text-yellow-400', to: '/incidents?category=electrical_hazard' },
    { label: 'Waste Management', icon: Trash2, color: 'text-emerald-400', to: '/incidents?category=waste_management' },
    { label: 'Extreme Heat', icon: Flame, color: 'text-rose-400', to: '/incidents?category=extreme_heat' },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 w-64 pt-16 bg-navy-950/95 border-r border-navy-800/80 flex flex-col transition-transform duration-200 ease-in-out md:static md:translate-x-0 md:pt-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex-1 flex flex-col justify-between overflow-y-auto px-3 py-4">
          <div className="space-y-6">
            {/* Primary Platform Views */}
            <div>
              <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
                Platform Console
              </p>
              <nav className="space-y-1">
                {primaryNavItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === '/incidents'}
                      onClick={onClose}
                      className={({ isActive }) =>
                        clsx(
                          'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all group',
                          isActive
                            ? 'bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/30 shadow-glow-cyan font-semibold'
                            : 'text-slate-400 hover:text-slate-100 hover:bg-navy-900 border border-transparent'
                        )
                      }
                    >
                      <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </nav>
            </div>

            {/* Incident Taxonomies */}
            <div>
              <p className="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
                Taxonomy Filters
              </p>
              <div className="space-y-1 px-1">
                {categories.map((cat) => {
                  const Icon = cat.icon;
                  return (
                    <NavLink
                      key={cat.label}
                      to={cat.to}
                      onClick={onClose}
                      className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-xs text-slate-400 hover:text-slate-200 hover:bg-navy-900/50 transition-colors"
                    >
                      <Icon className={clsx('w-3.5 h-3.5', cat.color)} />
                      <span>{cat.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            </div>
          </div>

          {/* User Status / Role Badge in Footer */}
          <div className="p-3 rounded-xl bg-navy-900/70 border border-navy-800/80 mt-6 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
              <span className="flex items-center gap-1.5 text-slate-400">
                <UserCheck className="w-3.5 h-3.5 text-brand-cyan" />
                Role:
              </span>
              <Badge variant={role === 'ADMIN' ? 'high' : role === 'ANALYST' ? 'medium' : 'cyan'} dot className="text-[10px]">
                {role}
              </Badge>
            </div>
            <p className="text-[10px] text-slate-500 truncate font-mono">
              {user ? user.email : 'Unauthenticated (Guest)'}
            </p>
          </div>
        </div>
      </aside>
    </>
  );
};
