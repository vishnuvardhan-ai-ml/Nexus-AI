import React, { useEffect, useRef, useCallback } from 'react';
import L from 'leaflet';
import { GeoIncidentFeature, BoundingBox } from '../../types';
import { createRiskMarkerIcon } from './RiskMarkerIcon';
import { createIncidentPopupHtml } from './IncidentMapPopup';
import { Maximize2, Plus, Minus, Navigation } from 'lucide-react';

interface LeafletMapContainerProps {
  features: GeoIncidentFeature[];
  bbox?: [number, number, number, number] | null; // [min_lng, min_lat, max_lng, max_lat]
  centerCoordinates?: [number, number] | null; // [lng, lat]
  onViewportChange?: (bbox: BoundingBox) => void;
  onMarkerSelect?: (feature: GeoIncidentFeature) => void;
  className?: string;
  enableViewportFilter?: boolean;
}

export const LeafletMapContainer: React.FC<LeafletMapContainerProps> = ({
  features,
  bbox,
  centerCoordinates,
  onViewportChange,
  onMarkerSelect,
  className = '',
  enableViewportFilter = false,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const debounceTimerRef = useRef<number | null>(null);

  // Initialize Leaflet Map Instance
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return; // already initialized

    // Default center (Bangalore coordinate fallback if empty)
    const initialLat = centerCoordinates ? centerCoordinates[1] : 12.9716;
    const initialLng = centerCoordinates ? centerCoordinates[0] : 77.5946;

    const map = L.map(mapContainerRef.current, {
      center: [initialLat, initialLng],
      zoom: 12,
      zoomControl: false, // We use custom cyber themed zoom controls
      attributionControl: true,
      maxBoundsViscosity: 0.8,
    });

    // CartoDB Dark Matter tile layer (matches #070b14 cyber theme)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank" rel="noopener noreferrer">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
      minZoom: 3,
    }).addTo(map);

    const markersGroup = L.layerGroup().addTo(map);
    markersLayerRef.current = markersGroup;
    mapInstanceRef.current = map;

    // Viewport change listener with debouncing
    const handleMoveEnd = () => {
      if (!onViewportChange || !enableViewportFilter) return;

      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = window.setTimeout(() => {
        const bounds = map.getBounds();
        onViewportChange({
          min_lat: Math.max(-90, bounds.getSouth()),
          min_lng: Math.max(-180, bounds.getWest()),
          max_lat: Math.min(90, bounds.getNorth()),
          max_lng: Math.min(180, bounds.getEast()),
        });
      }, 350);
    };

    map.on('moveend', handleMoveEnd);

    // ResizeObserver to handle container resizing reliably
    const resizeObserver = new ResizeObserver(() => {
      map.invalidateSize();
    });
    resizeObserver.observe(mapContainerRef.current);

    // Initial size invalidation after mount
    setTimeout(() => {
      map.invalidateSize();
    }, 150);

    return () => {
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current);
      }
      resizeObserver.disconnect();
      map.off('moveend', handleMoveEnd);
      map.remove();
      mapInstanceRef.current = null;
      markersLayerRef.current = null;
    };
  }, []); // Run once on mount

  // Update Markers when features prop changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersGroup = markersLayerRef.current;
    if (!map || !markersGroup) return;

    markersGroup.clearLayers();

    const latLngs: L.LatLng[] = [];

    features.forEach((feature) => {
      // GeoJSON RFC 7946: coordinates are [longitude, latitude]
      const lng = feature.geometry.coordinates[0];
      const lat = feature.geometry.coordinates[1];

      // Leaflet expects [latitude, longitude]
      const latLng = L.latLng(lat, lng);
      latLngs.push(latLng);

      const icon = createRiskMarkerIcon(feature);
      const marker = L.marker(latLng, { icon });

      // Create rich HTML popup
      const popupHtml = createIncidentPopupHtml(feature);
      marker.bindPopup(popupHtml, {
        maxWidth: 320,
        minWidth: 280,
        className: 'nexus-map-popup',
      });

      marker.on('click', () => {
        if (onMarkerSelect) {
          onMarkerSelect(feature);
        }
      });

      marker.addTo(markersGroup);
    });

    // Auto-fit bounds if features exist and map hasn't been manually panned by user
    if (latLngs.length > 0 && bbox) {
      // bbox: [min_lng, min_lat, max_lng, max_lat]
      const corner1 = L.latLng(bbox[1], bbox[0]);
      const corner2 = L.latLng(bbox[3], bbox[2]);
      const bounds = L.latLngBounds(corner1, corner2);
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
      }
    } else if (latLngs.length === 1) {
      map.setView(latLngs[0], 14);
    }
  }, [features, bbox, onMarkerSelect]);

  // Zoom control handlers
  const handleZoomIn = useCallback(() => {
    mapInstanceRef.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    mapInstanceRef.current?.zoomOut();
  }, []);

  const handleFitBounds = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (bbox) {
      const corner1 = L.latLng(bbox[1], bbox[0]);
      const corner2 = L.latLng(bbox[3], bbox[2]);
      const bounds = L.latLngBounds(corner1, corner2);
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
        return;
      }
    }

    if (centerCoordinates) {
      map.setView([centerCoordinates[1], centerCoordinates[0]], 12);
    }
  }, [bbox, centerCoordinates]);

  return (
    <div className={`relative w-full h-full overflow-hidden ${className}`}>
      {/* Map Canvas */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Cyber Themed Floating Map Controls (Top Right) */}
      <div className="absolute top-4 right-4 z-20 flex flex-col gap-2">
        <div className="flex flex-col rounded-xl overflow-hidden glass-panel border border-navy-800 shadow-glow-card">
          <button
            type="button"
            onClick={handleZoomIn}
            className="p-2.5 text-slate-300 hover:text-brand-cyan hover:bg-navy-800/80 transition-colors border-b border-navy-800/80"
            title="Zoom In"
            aria-label="Zoom In"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleZoomOut}
            className="p-2.5 text-slate-300 hover:text-brand-cyan hover:bg-navy-800/80 transition-colors"
            title="Zoom Out"
            aria-label="Zoom Out"
          >
            <Minus className="w-4 h-4" />
          </button>
        </div>

        <button
          type="button"
          onClick={handleFitBounds}
          className="p-2.5 rounded-xl glass-panel border border-navy-800 text-slate-300 hover:text-brand-cyan hover:bg-navy-800/80 transition-colors shadow-glow-card"
          title="Fit All Plotted Incidents"
          aria-label="Fit Bounds"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
