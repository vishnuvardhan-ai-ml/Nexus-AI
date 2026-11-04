import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, ArrowLeft, ArrowUpRight, LucideIcon } from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

interface PlaceholderPageProps {
  title: string;
  subtitle: string;
  milestone: string;
  icon: LucideIcon;
  plannedFeatures: string[];
}

export const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  subtitle,
  milestone,
  icon: Icon,
  plannedFeatures,
}) => {
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="text-slate-400 hover:text-brand-cyan transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">{title}</h1>
            <Badge variant="cyan" dot>
              {milestone}
            </Badge>
          </div>
          <p className="text-sm text-slate-400 mt-1">{subtitle}</p>
        </div>
      </div>

      <div className="glass-panel rounded-xl p-8 border border-navy-800 relative overflow-hidden">
        <div className="flex items-start gap-5">
          <div className="p-4 rounded-xl bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan shadow-glow-cyan shrink-0">
            <Icon className="w-8 h-8" />
          </div>

          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-white">Module Architecture Defined</h2>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                This civic module is mapped in the monorepo routing architecture and will be fully unlocked in the subsequent development milestone.
              </p>
            </div>

            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-brand-sky font-semibold mb-2">
                Planned Functional Capabilities:
              </h3>
              <ul className="space-y-2">
                {plannedFeatures.map((feat, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-xs text-slate-300">
                    <ShieldCheck className="w-4 h-4 text-brand-cyan shrink-0 mt-0.5" />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-4 flex items-center gap-3">
              <Link to="/dashboard">
                <Button size="sm" variant="primary">
                  Return to Dashboard Overview
                </Button>
              </Link>
              <Link to="/">
                <Button size="sm" variant="secondary">
                  Inspect Platform Architecture
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
