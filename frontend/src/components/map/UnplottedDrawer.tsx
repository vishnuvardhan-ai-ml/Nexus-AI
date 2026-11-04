import React from 'react';
import { Link } from 'react-router-dom';
import {
  X,
  AlertTriangle,
  MapPinOff,
  ExternalLink,
  Info,
  Calendar,
  Layers,
} from 'lucide-react';
import { UnplottedIncidentSummary } from '../../types';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';

interface UnplottedDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  unplottedItems: UnplottedIncidentSummary[];
  unplottedCount: number;
}

export const UnplottedDrawer: React.FC<UnplottedDrawerProps> = ({
  isOpen,
  onClose,
  unplottedItems,
  unplottedCount,
}) => {
  if (!isOpen) return null;

  const reasonLabels: Record<string, { label: string; variant: 'medium' | 'high' | 'neutral' }> = {
    MISSING_COORDINATES: { label: 'Awaiting Coordinates (Text Address Only)', variant: 'medium' },
    OUT_OF_BOUNDS_COORDINATES: { label: 'Invalid WGS84 Latitude/Longitude Range', variant: 'high' },
    INVALID_COORDINATE_FORMAT: { label: 'Malformed Coordinate Format', variant: 'high' },
    NON_FINITE_COORDINATES: { label: 'Non-Finite Coordinate Value (NaN/Inf)', variant: 'high' },
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer Container */}
      <aside className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-navy-950 border-l border-navy-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-5 border-b border-navy-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
              <MapPinOff className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                Unplotted Incident Reports
                <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-amber-950/80 text-amber-300 border border-amber-500/30">
                  {unplottedCount}
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Incidents in database currently missing verified WGS84 GPS coordinates.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-navy-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mandatory Data Integrity Banner */}
        <div className="bg-navy-900/90 border-b border-amber-500/20 p-4 text-xs text-amber-300 font-mono flex items-start gap-2.5">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>MANDATORY DATA INTEGRITY RULE:</strong> These incidents cannot be plotted on the Leaflet map until valid coordinates are supplied. NEXUS AI never invents coordinates or silently pins them at map center.
          </p>
        </div>

        {/* Incident List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {unplottedItems.length === 0 ? (
            <div className="text-center py-12 text-slate-500 font-mono text-xs">
              <p>No unplotted incidents in the current query batch.</p>
            </div>
          ) : (
            unplottedItems.map((item) => {
              const reasonInfo = reasonLabels[item.reason] || {
                label: item.reason,
                variant: 'medium',
              };

              return (
                <div
                  key={item.id}
                  className="p-4 rounded-xl bg-navy-900/50 border border-navy-800 hover:border-navy-700 transition-colors space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[10px] font-mono uppercase text-brand-cyan font-bold tracking-wider block mb-1">
                        {item.category.replace('_', ' ')}
                      </span>
                      <h4 className="text-sm font-bold text-white leading-tight">
                        {item.title}
                      </h4>
                    </div>

                    <Badge variant={reasonInfo.variant}>
                      {item.severity}
                    </Badge>
                  </div>

                  {/* Failure Reason Badge */}
                  <div className="p-2 rounded-lg bg-navy-950/80 border border-navy-800/80 text-[11px] font-mono text-slate-400">
                    <span className="text-amber-400 font-semibold block mb-0.5">Status:</span>
                    <span>{reasonInfo.label}</span>
                  </div>

                  {/* Location Text */}
                  <div className="text-xs text-slate-300 flex items-start gap-1.5">
                    <span className="text-slate-500 shrink-0">📍</span>
                    <span className="font-medium text-slate-200">{item.location_name}</span>
                  </div>

                  {/* Metadata & Direct Link */}
                  <div className="pt-2 border-t border-navy-800/60 flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span>{item.id}</span>
                    <Link
                      to={`/incidents/${item.id}`}
                      className="inline-flex items-center gap-1 text-brand-cyan hover:underline"
                    >
                      <span>Inspect Report</span>
                      <ExternalLink className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-navy-800 bg-navy-950 flex justify-end">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close Drawer
          </Button>
        </div>
      </aside>
    </>
  );
};
