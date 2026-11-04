import React from 'react';
import {
  Filter,
  RefreshCw,
  X,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
  ShieldCheck,
  Compass,
} from 'lucide-react';
import { IncidentCategory, RiskLevel, IncidentStatus } from '../../types';
import { Button } from '../ui/Button';

interface MapFilterToolbarProps {
  selectedCategory: string;
  onCategoryChange: (cat: string) => void;
  selectedRiskLevel: string;
  onRiskLevelChange: (level: string) => void;
  selectedStatus: string;
  onStatusChange: (status: string) => void;
  viewportFilterActive: boolean;
  onToggleViewportFilter: () => void;
  onlyOwnActive: boolean;
  onToggleOnlyOwn: () => void;
  onResetFilters: () => void;
  onRefresh: () => void;
  loading: boolean;
  geocodedCount: number;
  unplottedCount: number;
  onOpenUnplottedDrawer: () => void;
}

export const MapFilterToolbar: React.FC<MapFilterToolbarProps> = ({
  selectedCategory,
  onCategoryChange,
  selectedRiskLevel,
  onRiskLevelChange,
  selectedStatus,
  onStatusChange,
  viewportFilterActive,
  onToggleViewportFilter,
  onlyOwnActive,
  onToggleOnlyOwn,
  onResetFilters,
  onRefresh,
  loading,
  geocodedCount,
  unplottedCount,
  onOpenUnplottedDrawer,
}) => {
  const hasActiveFilters =
    Boolean(selectedCategory) ||
    Boolean(selectedRiskLevel) ||
    Boolean(selectedStatus) ||
    viewportFilterActive ||
    onlyOwnActive;

  return (
    <div className="glass-panel p-3.5 rounded-xl border border-navy-800 shadow-glow-card backdrop-blur-md flex flex-wrap items-center justify-between gap-3 text-xs">
      {/* Filter Selectors */}
      <div className="flex flex-wrap items-center gap-2.5">
        <div className="flex items-center gap-1.5 text-slate-400 font-mono font-medium">
          <Filter className="w-3.5 h-3.5 text-brand-cyan" />
          <span>Filters:</span>
        </div>

        {/* Category Filter */}
        <select
          value={selectedCategory}
          onChange={(e) => onCategoryChange(e.target.value)}
          className="bg-navy-900 border border-navy-800 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:border-brand-cyan"
        >
          <option value="">All Categories</option>
          <option value="waterlogging">Waterlogging</option>
          <option value="road_damage">Road Damage</option>
          <option value="electrical_hazard">Electrical Hazard</option>
          <option value="waste_management">Waste Management</option>
          <option value="extreme_heat">Extreme Heat</option>
        </select>

        {/* Risk Level Filter (Includes NOT_ASSESSED) */}
        <select
          value={selectedRiskLevel}
          onChange={(e) => onRiskLevelChange(e.target.value)}
          className="bg-navy-900 border border-navy-800 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:border-brand-cyan"
        >
          <option value="">All Risk Tiers</option>
          <option value="HIGH">HIGH Risk (≥ 60)</option>
          <option value="MEDIUM">MEDIUM Risk (30–59)</option>
          <option value="LOW">LOW Risk (&lt; 30)</option>
        </select>

        {/* Incident Mitigation Status */}
        <select
          value={selectedStatus}
          onChange={(e) => onStatusChange(e.target.value)}
          className="bg-navy-900 border border-navy-800 text-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium focus:outline-none focus:border-brand-cyan"
        >
          <option value="">All Statuses</option>
          <option value="reported">Reported</option>
          <option value="investigating">Investigating</option>
          <option value="mitigating">Mitigating</option>
          <option value="resolved">Resolved</option>
        </select>

        {/* Viewport Bounding Box Toggle */}
        <button
          type="button"
          onClick={onToggleViewportFilter}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
            viewportFilterActive
              ? 'bg-brand-cyan/20 border-brand-cyan text-brand-cyan shadow-[0_0_10px_-2px_rgba(0,240,255,0.4)]'
              : 'bg-navy-900 border-navy-800 text-slate-400 hover:text-slate-200'
          }`}
          title="Filter results to current map bounding box"
        >
          <Compass className="w-3.5 h-3.5" />
          <span>Viewport Only</span>
        </button>

        {/* Only My Submissions Toggle */}
        <button
          type="button"
          onClick={onToggleOnlyOwn}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-medium transition-colors ${
            onlyOwnActive
              ? 'bg-brand-sky/20 border-brand-sky text-brand-sky'
              : 'bg-navy-900 border-navy-800 text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>My Reports</span>
        </button>

        {/* Reset Filters Action */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="flex items-center gap-1 text-slate-400 hover:text-rose-400 px-2 py-1 transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        )}
      </div>

      {/* Right Actions: Counts & Refresh */}
      <div className="flex items-center gap-2">
        {/* Geocoded Count Badge */}
        <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-navy-900 border border-navy-800 text-[11px] font-mono text-slate-300">
          <span className="w-2 h-2 rounded-full bg-brand-cyan animate-pulse" />
          <span>{geocodedCount} Plotted</span>
        </div>

        {/* Unplotted Drawer Button */}
        {unplottedCount > 0 && (
          <button
            type="button"
            onClick={onOpenUnplottedDrawer}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-950/40 border border-amber-500/30 text-[11px] font-mono text-amber-300 hover:bg-amber-950/60 transition-colors"
            title="View incidents lacking GPS coordinates"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            <span>{unplottedCount} Awaiting GPS</span>
          </button>
        )}

        {/* Refresh Action */}
        <Button
          size="sm"
          variant="outline"
          onClick={onRefresh}
          disabled={loading}
          className="text-xs px-2.5 py-1"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-brand-cyan' : ''}`} />
          <span className="hidden sm:inline ml-1">Refresh</span>
        </Button>
      </div>
    </div>
  );
};
