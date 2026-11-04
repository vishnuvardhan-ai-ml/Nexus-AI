/**
 * Custom SVG DivIcon generator for Leaflet Risk Markers.
 * Reflects risk level colors, pulsing animations, and coordinate precision styles.
 */
import L from 'leaflet';
import { GeoIncidentFeature } from '../../types';

export function createRiskMarkerIcon(feature: GeoIncidentFeature): L.DivIcon {
  const p = feature.properties;
  const isHigh = p.risk_level === 'HIGH';
  const isMed = p.risk_level === 'MEDIUM';
  const isLow = p.risk_level === 'LOW';
  const isNotAssessed = p.assessment_status === 'NOT_ASSESSED' || !p.risk_level;
  const isGeneralized = p.precision === 'GENERALIZED';

  // Base colors by risk level
  let borderColor = '#64748b'; // default slate for NOT_ASSESSED
  let bgColor = 'rgba(15, 23, 42, 0.9)';
  let glowColor = 'rgba(100, 116, 139, 0.4)';
  let iconColor = '#94a3b8';

  if (isHigh) {
    borderColor = '#f43f5e'; // rose-500
    bgColor = 'rgba(244, 63, 94, 0.25)';
    glowColor = 'rgba(244, 63, 94, 0.6)';
    iconColor = '#fda4af';
  } else if (isMed) {
    borderColor = '#f59e0b'; // amber-500
    bgColor = 'rgba(245, 158, 11, 0.25)';
    glowColor = 'rgba(245, 158, 11, 0.5)';
    iconColor = '#fde68a';
  } else if (isLow) {
    borderColor = '#00f0ff'; // brand-cyan
    bgColor = 'rgba(0, 240, 255, 0.25)';
    glowColor = 'rgba(0, 240, 255, 0.5)';
    iconColor = '#00f0ff';
  }

  // Category SVG glyphs
  const categoryIcons: Record<string, string> = {
    waterlogging: `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"></path>
      </svg>
    `,
    road_damage: `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
        <line x1="12" y1="9" x2="12" y2="13"></line>
        <line x1="12" y1="17" x2="12.01" y2="17"></line>
      </svg>
    `,
    electrical_hazard: `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
      </svg>
    `,
    waste_management: `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 6h18"></path>
        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
      </svg>
    `,
    extreme_heat: `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${iconColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path>
      </svg>
    `,
  };

  const iconSvg = categoryIcons[p.category] || categoryIcons.road_damage;

  // Border style: dashed for generalized coordinates (~1km privacy buffer), solid for exact
  const borderStyle = isGeneralized ? 'dashed' : 'solid';
  const pulseClass = isHigh ? 'marker-pulse-high' : '';

  const html = `
    <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
      <!-- Outer pin ring -->
      <div class="${pulseClass}" style="
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: ${bgColor};
        border: 2px ${borderStyle} ${borderColor};
        box-shadow: 0 0 10px ${glowColor};
        display: flex;
        align-items: center;
        justify-content: center;
        backdrop-filter: blur(4px);
        transition: transform 0.15s ease;
      ">
        ${iconSvg}
      </div>

      <!-- Generalized coordinate indicator badge (small dash icon) -->
      ${
        isGeneralized
          ? `<div style="
              position: absolute;
              bottom: -2px;
              right: -2px;
              width: 10px;
              height: 10px;
              border-radius: 50%;
              background: #fbbf24;
              border: 1px solid #070b14;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 7px;
              font-weight: bold;
              color: #070b14;
            ">~</div>`
          : ''
      }
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-nexus-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
}
