import React from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ExternalLink,
  MapPin,
  Clock,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  X,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
} from 'lucide-react';
import { GeoIncidentFeature } from '../../types';
import { Badge } from '../ui/Badge';

interface IncidentMapPopupProps {
  feature: GeoIncidentFeature;
  onClose?: () => void;
  className?: string;
}

export const IncidentMapPopup: React.FC<IncidentMapPopupProps> = ({
  feature,
  onClose,
  className = '',
}) => {
  const p = feature.properties;

  const categoryIcons: Record<string, React.ReactNode> = {
    waterlogging: <Droplets className="w-3.5 h-3.5 text-sky-400" />,
    road_damage: <Construction className="w-3.5 h-3.5 text-amber-400" />,
    electrical_hazard: <Zap className="w-3.5 h-3.5 text-yellow-400" />,
    waste_management: <Trash2 className="w-3.5 h-3.5 text-emerald-400" />,
    extreme_heat: <Flame className="w-3.5 h-3.5 text-rose-400" />,
  };

  const categoryLabels: Record<string, string> = {
    waterlogging: 'Waterlogging & Flooding',
    road_damage: 'Road & Infrastructure Damage',
    electrical_hazard: 'Electrical Hazard',
    waste_management: 'Waste & Sanitation',
    extreme_heat: 'Extreme Heat',
  };

  const isExact = p.precision === 'EXACT';
  const isAssessed = p.assessment_status === 'ASSESSED' && p.risk_score !== null && p.risk_level !== null;

  const formattedDate = p.created_at
    ? new Date(p.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

  return (
    <div
      className={`font-sans p-4 rounded-xl bg-navy-950 border border-brand-cyan/20 shadow-2xl text-slate-200 min-w-[280px] max-w-[320px] ${className}`}
    >
      {/* Header Bar */}
      <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-navy-800">
        <div className="flex items-center gap-1.5">
          {categoryIcons[p.category] || <AlertTriangle className="w-3.5 h-3.5 text-brand-cyan" />}
          <span className="text-[11px] font-mono font-bold uppercase text-brand-cyan tracking-wider">
            {categoryLabels[p.category] || p.category}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <Badge
            variant={
              p.status === 'resolved'
                ? 'low'
                : p.status === 'mitigating'
                ? 'cyan'
                : p.status === 'investigating'
                ? 'medium'
                : 'neutral'
            }
          >
            {p.status}
          </Badge>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-white p-0.5 rounded transition-colors"
              aria-label="Close popup"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Incident Title */}
      <h4 className="text-sm font-bold text-white leading-snug mt-2.5 mb-2">
        {p.title}
      </h4>

      {/* Location Landmark */}
      <div className="text-xs text-slate-300 space-y-1 mb-3">
        <div className="flex items-start gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
          <span className="font-medium text-slate-200">{p.location_name}</span>
        </div>

        {formattedDate && (
          <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono">
            <Clock className="w-3 h-3 text-slate-500" />
            <span>Reported: {formattedDate}</span>
          </div>
        )}
      </div>

      {/* Metadata Badges: Precision & Ownership */}
      <div className="flex flex-wrap items-center gap-1.5 mb-3">
        {isExact ? (
          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            EXACT GPS
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-300 bg-amber-950/60 border border-amber-500/30 px-2 py-0.5 rounded">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            GENERALIZED (~1km)
          </span>
        )}

        {p.is_own_incident && (
          <span className="text-[10px] font-mono text-brand-cyan bg-cyan-950/60 border border-brand-cyan/30 px-2 py-0.5 rounded">
            YOUR REPORT
          </span>
        )}

        <Badge variant={p.severity === 'HIGH' ? 'high' : p.severity === 'MEDIUM' ? 'medium' : 'low'}>
          {p.severity}
        </Badge>
      </div>

      {/* Authoritative Risk Assessment Box (Only if ASSESSED) */}
      {isAssessed ? (
        <div className="p-3 rounded-lg bg-navy-900/80 border border-brand-cyan/20 space-y-2 mb-3">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
              Authoritative Risk Score
            </span>
            <Badge
              variant={
                p.risk_level === 'HIGH' ? 'high' : p.risk_level === 'MEDIUM' ? 'medium' : 'low'
              }
            >
              {p.risk_level}
            </Badge>
          </div>

          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-black font-mono text-white tracking-tight">
              {p.risk_score?.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400 font-mono">/ 100</span>
          </div>

          {p.primary_driver && (
            <div className="text-[11px] text-slate-300 pt-1 border-t border-navy-800">
              <span className="text-slate-400 font-mono text-[10px] uppercase">Primary Driver: </span>
              <strong className="text-white font-medium">{p.primary_driver}</strong>
            </div>
          )}
        </div>
      ) : (
        /* Mandatory Rule: Never show risk score for NOT_ASSESSED records */
        <div className="p-3 rounded-lg bg-navy-900/40 border border-dashed border-slate-700 text-center mb-3">
          <span className="inline-block text-[10px] font-mono uppercase font-semibold text-slate-400 bg-slate-800/80 border border-slate-700 px-2.5 py-0.5 rounded">
            STATUS: NOT ASSESSED
          </span>
          <p className="text-[11px] text-slate-400 mt-1.5 mb-0">
            No calculated risk score available.
          </p>
        </div>
      )}

      {/* Direct Link to Incident Details */}
      <div className="pt-2.5 border-t border-navy-800/80">
        <Link
          to={`/incidents/${p.id}`}
          className="flex items-center justify-center gap-1.5 w-full py-2 px-3 rounded-lg bg-brand-cyan hover:bg-cyan-300 text-navy-950 font-bold text-xs transition-colors shadow-[0_0_15px_-3px_rgba(0,240,255,0.4)]"
        >
          <span>View Full Incident & Risk Intel</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
};

export function createIncidentPopupHtml(feature: GeoIncidentFeature): string {
  const p = feature.properties;

  const categoryLabels: Record<string, string> = {
    waterlogging: 'Waterlogging & Flooding',
    road_damage: 'Road & Infrastructure Damage',
    electrical_hazard: 'Electrical Hazard',
    waste_management: 'Waste & Sanitation',
    extreme_heat: 'Extreme Heat',
  };
  const categoryName = categoryLabels[p.category] || p.category;

  const statusColors: Record<string, { bg: string; text: string; border: string }> = {
    reported: { bg: 'rgba(56, 189, 248, 0.1)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)' },
    investigating: { bg: 'rgba(245, 158, 11, 0.1)', text: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' },
    mitigating: { bg: 'rgba(168, 85, 247, 0.1)', text: '#c084fc', border: 'rgba(168, 85, 247, 0.3)' },
    resolved: { bg: 'rgba(16, 185, 129, 0.1)', text: '#34d399', border: 'rgba(16, 185, 129, 0.3)' },
  };
  const statStyle = statusColors[p.status] || statusColors.reported;

  let riskSectionHtml = '';
  if (p.assessment_status === 'ASSESSED' && p.risk_score !== null && p.risk_level !== null) {
    const riskLevelColors: Record<string, { text: string; bg: string; border: string }> = {
      LOW: { text: '#34d399', bg: 'rgba(16, 185, 129, 0.15)', border: 'rgba(16, 185, 129, 0.3)' },
      MEDIUM: { text: '#fbbf24', bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.3)' },
      HIGH: { text: '#f43f5e', bg: 'rgba(244, 63, 94, 0.15)', border: 'rgba(244, 63, 94, 0.3)' },
    };
    const rStyle = riskLevelColors[p.risk_level] || riskLevelColors.MEDIUM;

    riskSectionHtml = `
      <div style="background: rgba(13, 21, 39, 0.9); border: 1px solid rgba(56, 189, 248, 0.15); border-radius: 8px; padding: 10px; margin-top: 10px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
          <span style="font-size: 10px; font-family: monospace; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px;">Authoritative Risk Score</span>
          <span style="font-size: 10px; font-family: monospace; font-weight: 700; color: ${rStyle.text}; background: ${rStyle.bg}; border: 1px solid ${rStyle.border}; padding: 1px 6px; border-radius: 4px;">
            ${p.risk_level}
          </span>
        </div>
        <div style="display: flex; align-items: baseline; gap: 6px;">
          <span style="font-size: 22px; font-weight: 900; font-family: monospace; color: #ffffff; letter-spacing: -0.5px;">
            ${p.risk_score.toFixed(1)}
          </span>
          <span style="font-size: 11px; color: #64748b; font-family: monospace;">/ 100</span>
        </div>
        ${
          p.primary_driver
            ? `<div style="font-size: 11px; color: #94a3b8; margin-top: 4px; font-family: sans-serif;">
                Primary Driver: <strong style="color: #e2e8f0;">${p.primary_driver}</strong>
              </div>`
            : ''
        }
      </div>
    `;
  } else {
    riskSectionHtml = `
      <div style="background: rgba(13, 21, 39, 0.6); border: 1px dashed rgba(148, 163, 184, 0.25); border-radius: 8px; padding: 10px; margin-top: 10px; text-align: center;">
        <span style="display: inline-block; font-size: 10px; font-family: monospace; font-weight: 600; color: #94a3b8; background: rgba(100, 116, 139, 0.15); border: 1px solid rgba(100, 116, 139, 0.3); padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">
          ASSESSMENT STATUS: NOT ASSESSED
        </span>
        <p style="font-size: 11px; color: #64748b; margin-top: 4px; margin-bottom: 0;">
          No calculated risk score available.
        </p>
      </div>
    `;
  }

  const isExact = p.precision === 'EXACT';
  const precisionHtml = isExact
    ? `<span style="font-size: 10px; font-family: monospace; color: #34d399; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); padding: 2px 6px; border-radius: 4px;">
        EXACT GPS
       </span>`
    : `<span style="font-size: 10px; font-family: monospace; color: #fbbf24; background: rgba(245, 158, 11, 0.1); border: 1px dashed rgba(245, 158, 11, 0.3); padding: 2px 6px; border-radius: 4px;">
        GENERALIZED (~1km)
       </span>`;

  const ownBadgeHtml = p.is_own_incident
    ? `<span style="font-size: 10px; font-family: monospace; color: #00f0ff; background: rgba(0, 240, 255, 0.1); border: 1px solid rgba(0, 240, 255, 0.25); padding: 2px 6px; border-radius: 4px;">
        YOUR REPORT
       </span>`
    : '';

  const dateStr = p.created_at
    ? new Date(p.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '';

  return `
    <div style="font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 14px; min-width: 260px; max-width: 310px; background: #0d1527; color: #f1f5f9; box-sizing: border-box;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 6px;">
        <span style="font-size: 10px; font-family: monospace; text-transform: uppercase; letter-spacing: 0.5px; color: #00f0ff; font-weight: 700;">
          ${categoryName}
        </span>
        <span style="font-size: 10px; font-family: monospace; text-transform: uppercase; font-weight: 600; color: ${statStyle.text}; background: ${statStyle.bg}; border: 1px solid ${statStyle.border}; padding: 1px 6px; border-radius: 4px;">
          ${p.status}
        </span>
      </div>

      <h4 style="font-size: 14px; font-weight: 700; color: #ffffff; line-height: 1.3; margin: 0 0 8px 0;">
        ${escapeHtml(p.title)}
      </h4>

      <div style="font-size: 11px; color: #94a3b8; line-height: 1.4; margin-bottom: 8px;">
        <div style="display: flex; align-items: flex-start; gap: 4px;">
          <span style="color: #64748b; shrink-0;">📍</span>
          <span style="color: #cbd5e1; font-weight: 500;">${escapeHtml(p.location_name)}</span>
        </div>
        ${dateStr ? `<div style="font-size: 10px; color: #64748b; margin-top: 3px; font-family: monospace;">Reported: ${dateStr}</div>` : ''}
      </div>

      <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-bottom: 8px;">
        ${precisionHtml}
        ${ownBadgeHtml}
      </div>

      ${riskSectionHtml}

      <div style="margin-top: 12px; border-top: 1px solid rgba(56, 189, 248, 0.12); padding-top: 10px;">
        <a href="/incidents/${p.id}" style="display: block; text-align: center; background: #00f0ff; color: #070b14; font-size: 11px; font-weight: 700; padding: 7px 12px; border-radius: 6px; text-decoration: none; transition: background 0.15s ease;">
          View Full Incident & Risk Intel →
        </a>
      </div>
    </div>
  `;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

