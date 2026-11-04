import React from 'react';
import { LucideIcon } from 'lucide-react';
import { clsx } from 'clsx';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: string;
    isPositive?: boolean;
    label?: string;
  };
  icon: LucideIcon;
  accentColor?: 'cyan' | 'blue' | 'amber' | 'rose' | 'emerald';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon: Icon,
  accentColor = 'cyan',
}) => {
  const accentIconStyles = {
    cyan: 'bg-brand-cyan/10 text-brand-cyan border-brand-cyan/30',
    blue: 'bg-brand-blue/10 text-brand-sky border-brand-blue/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  };

  return (
    <div className="glass-panel glass-panel-hover rounded-xl p-5 relative overflow-hidden">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</p>
          <h3 className="text-2xl font-bold font-mono text-white mt-1 tracking-tight">{value}</h3>
          {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
        </div>
        <div className={clsx('p-2.5 rounded-lg border', accentIconStyles[accentColor])}>
          <Icon className="w-5 h-5" />
        </div>
      </div>

      {trend && (
        <div className="mt-4 pt-3 border-t border-navy-700/60 flex items-center gap-1.5 text-xs">
          <span
            className={clsx(
              'font-semibold font-mono',
              trend.isPositive ? 'text-emerald-400' : 'text-rose-400'
            )}
          >
            {trend.value}
          </span>
          {trend.label && <span className="text-slate-400">{trend.label}</span>}
        </div>
      )}
    </div>
  );
};
