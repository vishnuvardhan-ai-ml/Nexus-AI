import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  MapPin,
  AlertTriangle,
  Layers,
  Info,
  ShieldCheck,
  Compass,
  MapPinOff,
  Sliders,
  ExternalLink,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getGeoIncidents, getGeoSummary } from '../services/api';
import {
  GeoIncidentFeature,
  GeoIncidentCollectionResponse,
  GeoSummaryResponse,
  BoundingBox,
  IncidentCategory,
  RiskLevel,
  IncidentStatus,
} from '../types';
import { LeafletMapContainer } from '../components/map/LeafletMapContainer';
import { MapFilterToolbar } from '../components/map/MapFilterToolbar';
import { UnplottedDrawer } from '../components/map/UnplottedDrawer';
import { IncidentMapPopup } from '../components/map/IncidentMapPopup';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';

export const RiskMapPage: React.FC = () => {
  const { token, role } = useAuth();

  // Geospatial Data State
  const [geoData, setGeoData] = useState<GeoIncidentCollectionResponse | null>(null);
  const [summary, setSummary] = useState<GeoSummaryResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filter States
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [viewportFilterActive, setViewportFilterActive] = useState<boolean>(false);
  const [currentViewportBbox, setCurrentViewportBbox] = useState<BoundingBox | null>(null);
  const [onlyOwnActive, setOnlyOwnActive] = useState<boolean>(false);

  // Unplotted Drawer & Selected Marker State
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [selectedFeature, setSelectedFeature] = useState<GeoIncidentFeature | null>(null);

  // Request race-condition prevention sequence
  const requestSeqRef = useRef<number>(0);

  // Fetch Summary Metrics once on mount / token change
  useEffect(() => {
    if (!token) return;
    getGeoSummary(token)
      .then((res) => setSummary(res))
      .catch((err) => console.warn('Could not load geo summary:', err));
  }, [token]);

  // Fetch GeoJSON Incidents with debouncing and sequence protection
  const fetchIncidents = useCallback(async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    const currentSeq = ++requestSeqRef.current;
    setLoading(true);
    setError(null);

    try {
      const params = {
        category: (selectedCategory || undefined) as IncidentCategory | undefined,
        risk_level: (selectedRiskLevel || undefined) as RiskLevel | undefined,
        status: (selectedStatus || undefined) as IncidentStatus | undefined,
        min_lat: viewportFilterActive && currentViewportBbox ? currentViewportBbox.min_lat : undefined,
        min_lng: viewportFilterActive && currentViewportBbox ? currentViewportBbox.min_lng : undefined,
        max_lat: viewportFilterActive && currentViewportBbox ? currentViewportBbox.max_lat : undefined,
        max_lng: viewportFilterActive && currentViewportBbox ? currentViewportBbox.max_lng : undefined,
        only_own: onlyOwnActive ? true : undefined,
        limit: 100,
      };

      const res = await getGeoIncidents(params, token);

      // Protect against out-of-order race conditions
      if (currentSeq === requestSeqRef.current) {
        setGeoData(res);
      }
    } catch (err: unknown) {
      if (currentSeq === requestSeqRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to retrieve geospatial data from server.');
      }
    } finally {
      if (currentSeq === requestSeqRef.current) {
        setLoading(false);
      }
    }
  }, [
    token,
    selectedCategory,
    selectedRiskLevel,
    selectedStatus,
    viewportFilterActive,
    currentViewportBbox,
    onlyOwnActive,
  ]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  // Viewport change from Leaflet container
  const handleViewportChange = useCallback((bbox: BoundingBox) => {
    setCurrentViewportBbox(bbox);
  }, []);

  const handleResetFilters = () => {
    setSelectedCategory('');
    setSelectedRiskLevel('');
    setSelectedStatus('');
    setViewportFilterActive(false);
    setCurrentViewportBbox(null);
    setOnlyOwnActive(false);
  };

  const geocodedFeatures = geoData?.features || [];
  const geocodedCount = geocodedFeatures.length;
  const unplottedCount = geoData?.unplotted_count || 0;
  const unplottedItems = geoData?.unplotted_items || [];
  const hasMore = geoData?.has_more || false;

  return (
    <div className="space-y-4 h-[calc(100vh-5rem)] flex flex-col">
      {/* Top Workspace Header & Geospatial Telemetry Summary */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan shadow-[0_0_15px_-3px_rgba(0,240,255,0.3)]">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
                Geospatial Risk Intelligence & Incident Map
                <Badge variant="cyan" dot>
                  WGS84 VERIFIED
                </Badge>
              </h1>
              <p className="text-xs text-slate-400">
                CartoDB Dark Matter GIS workspace mapping verified community hazards, risk scores, and geographic concentrations.
              </p>
            </div>
          </div>
        </div>

        {/* High-level Coverage Telemetry Chips */}
        {summary && (
          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            <div className="p-2 rounded-xl glass-panel border border-navy-800 text-right min-w-[90px]">
              <span className="text-[10px] uppercase font-mono text-slate-400 block">GPS Coverage</span>
              <span className="text-sm font-bold font-mono text-brand-cyan">
                {summary.coverage_percentage}%
              </span>
              <span className="text-[9px] font-mono text-slate-500 block">
                ({summary.geocoded_count}/{summary.total_incidents})
              </span>
            </div>
            <div className="p-2 rounded-xl glass-panel border border-navy-800 text-right min-w-[90px]">
              <span className="text-[10px] uppercase font-mono text-slate-400 block">High Risk</span>
              <span className="text-sm font-bold font-mono text-rose-400">
                {summary.high_risk_count}
              </span>
            </div>
            <div className="p-2 rounded-xl glass-panel border border-navy-800 text-right min-w-[90px]">
              <span className="text-[10px] uppercase font-mono text-slate-400 block">Total Reports</span>
              <span className="text-sm font-bold font-mono text-white">
                {summary.total_incidents}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Filter Toolbar */}
      <div className="shrink-0">
        <MapFilterToolbar
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          selectedRiskLevel={selectedRiskLevel}
          onRiskLevelChange={setSelectedRiskLevel}
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
          viewportFilterActive={viewportFilterActive}
          onToggleViewportFilter={() => setViewportFilterActive(!viewportFilterActive)}
          onlyOwnActive={onlyOwnActive}
          onToggleOnlyOwn={() => setOnlyOwnActive(!onlyOwnActive)}
          onResetFilters={handleResetFilters}
          onRefresh={fetchIncidents}
          loading={loading}
          geocodedCount={geocodedCount}
          unplottedCount={unplottedCount}
          onOpenUnplottedDrawer={() => setDrawerOpen(true)}
        />
      </div>

      {/* Result Truncation Warning (has_more) */}
      {hasMore && (
        <div className="shrink-0 bg-navy-900/90 border border-amber-500/30 rounded-xl px-4 py-2.5 flex items-center justify-between text-xs text-amber-300 font-mono">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>QUERY WINDOW TRUNCATION:</strong> The server returned {geoData?.limit_applied || 100} records (batch limit). Additional incidents exist beyond this window. Zoom in or filter by category to view localized incidents.
            </span>
          </div>
          <button
            type="button"
            onClick={() => setViewportFilterActive(true)}
            className="text-brand-cyan hover:underline shrink-0 ml-3"
          >
            Activate Viewport Filter →
          </button>
        </div>
      )}

      {/* Main Map Canvas Area */}
      <div className="relative flex-1 w-full rounded-2xl overflow-hidden border border-navy-800 glass-panel shadow-glow-card min-h-[420px]">
        {/* Leaflet Map Component */}
        <LeafletMapContainer
          features={geocodedFeatures}
          bbox={geoData?.bbox}
          centerCoordinates={geoData?.center_coordinates}
          onViewportChange={handleViewportChange}
          onMarkerSelect={(feat) => setSelectedFeature(feat)}
          enableViewportFilter={viewportFilterActive}
          className="w-full h-full"
        />

        {/* Selected Incident Inspector Overlay (When Marker Selected) */}
        {selectedFeature && (
          <div className="absolute top-4 left-4 z-30 shadow-2xl animate-in fade-in duration-150">
            <IncidentMapPopup
              feature={selectedFeature}
              onClose={() => setSelectedFeature(null)}
            />
          </div>
        )}

        {/* State Overlays: Authentication Required, Service Error, or Filtered View */}
        {!token && (
          <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center p-6 bg-navy-950/80 backdrop-blur-sm">
            <div className="pointer-events-auto max-w-md p-6 rounded-2xl glass-panel border border-brand-cyan/30 text-center space-y-3 shadow-2xl">
              <div className="w-12 h-12 rounded-xl bg-navy-800 border border-brand-cyan/40 flex items-center justify-center text-brand-cyan mx-auto">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">Authentication Required</h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                Sign in with an authorized account to access the Geospatial Risk Intelligence Map and live incident coordinates.
              </p>
              <div className="pt-2">
                <Link to="/login">
                  <Button size="sm" variant="primary">
                    <span>Sign In to Access Map</span>
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        )}

        {token && error && (
          <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center p-6 bg-navy-950/80 backdrop-blur-sm">
            <div className="pointer-events-auto max-w-md p-6 rounded-2xl glass-panel border border-rose-500/40 text-center space-y-3 shadow-2xl">
              <div className="w-12 h-12 rounded-xl bg-navy-800 border border-rose-500/40 flex items-center justify-center text-rose-400 mx-auto">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white">Geospatial Service Unavailable</h3>
              <p className="text-xs text-rose-300/90 leading-relaxed font-mono">
                {error}
              </p>
              <div className="pt-2">
                <Button size="sm" variant="secondary" onClick={fetchIncidents}>
                  <span>Retry Connection</span>
                </Button>
              </div>
            </div>
          </div>
        )}

        {token && !loading && !error && geocodedCount === 0 && (
          <div className="absolute inset-0 z-20 pointer-events-none flex items-center justify-center p-6 bg-navy-950/60 backdrop-blur-[2px]">
            <div className="pointer-events-auto max-w-md p-6 rounded-2xl glass-panel border border-navy-700 text-center space-y-3 shadow-2xl">
              <div className="w-12 h-12 rounded-xl bg-navy-800 border border-navy-700 flex items-center justify-center text-slate-400 mx-auto">
                <MapPinOff className="w-6 h-6 text-brand-cyan" />
              </div>
              <h3 className="text-base font-bold text-white">No Mapped Incidents in View</h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {unplottedCount > 0
                  ? `There are ${unplottedCount} community reports in the database that lack device GPS coordinates. Open the unplotted drawer to view them.`
                  : 'No incidents match your current filter parameters or geographic viewport.'}
              </p>
              <div className="flex items-center justify-center gap-2 pt-1">
                {unplottedCount > 0 && (
                  <Button size="sm" variant="outline" onClick={() => setDrawerOpen(true)}>
                    <span>View {unplottedCount} Unplotted Reports</span>
                  </Button>
                )}
                <Button size="sm" variant="secondary" onClick={handleResetFilters}>
                  Reset All Filters
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Map Legend Overlay (Bottom Left) */}
        <div className="absolute bottom-4 left-4 z-20 pointer-events-auto max-w-xs p-3.5 rounded-xl glass-panel border border-navy-800 shadow-glow-card backdrop-blur-md text-[11px] font-mono space-y-2">
          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center justify-between pb-1.5 border-b border-navy-800">
            <span>Risk Marker Legend</span>
            <span className="text-[9px] text-brand-cyan">RFC 7946</span>
          </div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-slate-300">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.8)] animate-pulse" />
              <span>HIGH (≥ 60)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.6)]" />
              <span>MEDIUM (30–59)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-brand-cyan shadow-[0_0_8px_rgba(0,240,255,0.6)]" />
              <span>LOW (&lt; 30)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-500 border border-slate-400" />
              <span>NOT ASSESSED</span>
            </div>
          </div>

          <div className="pt-2 border-t border-navy-800 flex items-center justify-between text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full border border-solid border-slate-300" />
              <span>Exact GPS</span>
            </span>
            <span className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full border border-dashed border-amber-400" />
              <span>Generalized (~1km)</span>
            </span>
          </div>
        </div>
      </div>

      {/* Unplotted Incidents Drawer */}
      <UnplottedDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        unplottedItems={unplottedItems}
        unplottedCount={unplottedCount}
      />
    </div>
  );
};
