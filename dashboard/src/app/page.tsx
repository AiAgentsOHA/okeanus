"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { useStore } from "@/lib/store";
import { entityColor, entityColorHex, severityBg, cn } from "@/lib/utils";
import {
  Layers,
  X,
  MapPin,
  Eye,
  EyeOff,
  AlertTriangle,
  Navigation,
} from "lucide-react";

interface Entity {
  id: string;
  name: string;
  entity_type: string;
  latitude: number;
  longitude: number;
  description?: string;
  [key: string]: unknown;
}

interface AlertItem {
  severity: string;
  title: string;
  description: string;
}

/* ===== Entity Count Overlay ===== */
function EntityCountOverlay({ entities }: { entities: Entity[] }) {
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    entities.forEach((e) => {
      const t = e.entity_type || "unknown";
      counts[t] = (counts[t] || 0) + 1;
    });
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [entities]);

  if (entities.length === 0) return null;

  return (
    <div className="absolute top-4 right-4 z-10 glass-strong rounded-xl p-3 min-w-[140px] animate-fade-in">
      <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-2">
        Entities Tracked
      </div>
      <div className="text-2xl font-bold font-mono text-text-primary mb-2">
        {entities.length.toLocaleString()}
      </div>
      <div className="space-y-1">
        {typeCounts.slice(0, 5).map(([type, count]) => (
          <div key={type} className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              <div
                className="w-1.5 h-1.5 rounded-full"
                style={{ backgroundColor: entityColorHex(type) }}
              />
              <span className="text-[10px] text-text-muted capitalize">{type}</span>
            </div>
            <span className="text-[10px] font-mono text-text-secondary">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== Compass Rose ===== */
function CompassRose({ bearing }: { bearing: number }) {
  return (
    <div className="absolute bottom-20 right-4 z-10 glass rounded-full w-12 h-12 flex items-center justify-center">
      <div
        className="compass-rose flex flex-col items-center"
        style={{ transform: `rotate(${-bearing}deg)` }}
      >
        <Navigation size={18} className="text-accent-cyan" fill="currentColor" />
        <span className="text-[7px] font-bold text-accent-cyan mt-[-2px]">N</span>
      </div>
    </div>
  );
}

/* ===== Scale Bar ===== */
function ScaleBar({ zoom }: { zoom: number }) {
  const metersPerPixel = (156543.03392 * Math.cos(0)) / Math.pow(2, zoom);
  const scaleWidthPx = 80;
  const scaleMeters = metersPerPixel * scaleWidthPx;

  let label: string;
  if (scaleMeters >= 1000) {
    label = `${Math.round(scaleMeters / 1000)} km`;
  } else {
    label = `${Math.round(scaleMeters)} m`;
  }

  return (
    <div className="absolute bottom-20 left-4 z-10 flex flex-col items-start">
      <span className="text-[9px] text-text-muted font-mono mb-0.5">{label}</span>
      <div className="scale-bar" style={{ width: `${scaleWidthPx}px`, height: "6px" }} />
    </div>
  );
}

/* ===== Coordinate Display ===== */
function CoordinateDisplay({ lat, lng }: { lat: number | null; lng: number | null }) {
  if (lat === null || lng === null) return null;
  const latDir = lat >= 0 ? "N" : "S";
  const lngDir = lng >= 0 ? "E" : "W";

  return (
    <div className="absolute bottom-14 left-1/2 -translate-x-1/2 z-10 glass rounded-lg px-3 py-1.5 animate-fade-in">
      <span className="font-mono text-[11px] text-text-secondary coord-display">
        {Math.abs(lat).toFixed(4)}&deg;{latDir}&nbsp;&nbsp;{Math.abs(lng).toFixed(4)}&deg;{lngDir}
      </span>
    </div>
  );
}

/* ===== Loading Shimmer ===== */
function LoadingShimmer() {
  return (
    <div className="absolute inset-0 flex items-center justify-center z-20">
      <div className="flex flex-col items-center gap-4">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 rounded-full border-2 border-accent-cyan/20 animate-ping" />
          <div className="absolute inset-1 rounded-full border-2 border-accent-cyan/30 border-t-accent-cyan animate-spin" />
          <div className="absolute inset-3 rounded-full border border-accent-blue/20 border-b-accent-blue animate-spin" style={{ animationDirection: "reverse", animationDuration: "1.5s" }} />
        </div>
        <div className="flex flex-col items-center gap-1.5">
          <span className="text-sm font-semibold text-text-secondary">Initializing Globe</span>
          <span className="text-xs text-text-muted">Loading ocean intelligence data...</span>
        </div>
        <div className="flex gap-1.5 mt-2">
          {[32, 48, 24, 40, 28].map((w, i) => (
            <div
              key={i}
              className="h-1 rounded-full shimmer"
              style={{ width: w, animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function GlobePage() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [hotspots, setHotspots] = useState<unknown[]>([]);
  const [density, setDensity] = useState<unknown[]>([]);
  const [mapReady, setMapReady] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [hoverCoords, setHoverCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [viewState, setViewState] = useState({
    longitude: 20,
    latitude: 0,
    zoom: 2.5,
    pitch: 35,
    bearing: 0,
  });
  const layers = useStore((s) => s.layers);
  const toggleLayer = useStore((s) => s.toggleLayer);
  const selectedEntity = useStore((s) => s.selectedEntity);
  const setSelectedEntity = useStore((s) => s.setSelectedEntity);
  const [layerPanelOpen, setLayerPanelOpen] = useState(true);

  useEffect(() => {
    const fetches = [
      fetch("/api/analytics/entities/density")
        .then((r) => r.json())
        .then((d) => { if (Array.isArray(d)) setEntities(d); })
        .catch(() => {}),
      fetch("/api/alerts?limit=20")
        .then((r) => r.json())
        .then((d) => { if (Array.isArray(d)) setAlerts(d); })
        .catch(() => {}),
      fetch("/api/analytics/hotspots")
        .then((r) => r.json())
        .then((d) => { if (Array.isArray(d)) setHotspots(d); })
        .catch(() => {}),
      fetch("/api/analytics/density")
        .then((r) => r.json())
        .then((d) => { if (Array.isArray(d)) setDensity(d); })
        .catch(() => {}),
    ];

    Promise.all(fetches).then(() => setDataLoaded(true));
    setMapReady(true);
  }, []);

  const onMapClick = useCallback(
    (info: { object?: Entity }) => {
      if (info.object) {
        setSelectedEntity(info.object as unknown as Record<string, unknown>);
      }
    },
    [setSelectedEntity]
  );

  const layerDefs = [
    { key: "entities" as const, label: "Entities", color: "bg-accent-cyan" },
    { key: "hotspots" as const, label: "Hotspots", color: "bg-accent-red" },
    { key: "density" as const, label: "Density", color: "bg-accent-emerald" },
    { key: "alerts" as const, label: "Alerts", color: "bg-accent-amber" },
    { key: "vessels" as const, label: "Vessels", color: "bg-accent-blue" },
  ];

  return (
    <div className="relative w-full h-full">
      <MapView
        viewState={viewState}
        onViewStateChange={(vs) => setViewState(vs as typeof viewState)}
        entities={layers.entities ? entities : []}
        hotspots={layers.hotspots ? hotspots : []}
        density={layers.density ? density : []}
        onEntityClick={onMapClick}
        ready={mapReady}
        onHover={(lat, lng) => setHoverCoords(lat !== null ? { lat, lng: lng! } : null)}
      />

      {!dataLoaded && <LoadingShimmer />}

      {!selectedEntity && dataLoaded && <EntityCountOverlay entities={entities} />}

      {/* Layer Controls */}
      <div className="absolute top-4 left-4 z-10">
        <button
          onClick={() => setLayerPanelOpen(!layerPanelOpen)}
          className="glass card-glow rounded-xl p-2.5 text-text-secondary hover:text-text-primary transition-colors"
        >
          <Layers size={18} />
        </button>
        {layerPanelOpen && (
          <div className="glass card-glow rounded-xl mt-2 p-3 w-48 animate-fade-in">
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
              Map Layers
            </div>
            {layerDefs.map((l) => (
              <button
                key={l.key}
                onClick={() => toggleLayer(l.key)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-bg-hover transition-all duration-200 text-left group"
              >
                {layers[l.key] ? (
                  <Eye size={14} className="text-text-secondary group-hover:text-accent-cyan transition-colors" />
                ) : (
                  <EyeOff size={14} className="text-text-muted" />
                )}
                <div className={cn("w-2 h-2 rounded-full transition-shadow", l.color, layers[l.key] && "shadow-[0_0_6px_currentColor]")} />
                <span className={cn("text-xs transition-colors", layers[l.key] ? "text-text-primary" : "text-text-muted")}>
                  {l.label}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      <CompassRose bearing={viewState.bearing} />
      <ScaleBar zoom={viewState.zoom} />
      {hoverCoords && <CoordinateDisplay lat={hoverCoords.lat} lng={hoverCoords.lng} />}

      {/* Entity Detail */}
      {selectedEntity && (
        <div className="absolute top-4 right-4 bottom-16 w-80 z-10 glass-strong gradient-border-active rounded-xl p-4 overflow-y-auto animate-slide-in-right">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor: entityColorHex((selectedEntity.entity_type as string) || ""),
                  boxShadow: `0 0 8px ${entityColorHex((selectedEntity.entity_type as string) || "")}60`,
                }}
              />
              <span className="text-[10px] font-mono uppercase text-text-muted">
                {(selectedEntity.entity_type as string) || "Entity"}
              </span>
            </div>
            <button onClick={() => setSelectedEntity(null)} className="text-text-muted hover:text-text-primary transition-colors">
              <X size={16} />
            </button>
          </div>
          <h3 className="text-lg font-semibold mb-2">{(selectedEntity.name as string) || "Unknown"}</h3>
          {selectedEntity.description && (
            <p className="text-sm text-text-secondary mb-4 leading-relaxed">{selectedEntity.description as string}</p>
          )}
          {selectedEntity.latitude && (
            <div className="flex items-center gap-1.5 text-xs text-text-muted mb-4">
              <MapPin size={12} />
              <span className="font-mono">
                {Number(selectedEntity.latitude).toFixed(4)}, {Number(selectedEntity.longitude).toFixed(4)}
              </span>
            </div>
          )}
          <div className="space-y-1.5">
            <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">Properties</div>
            {Object.entries(selectedEntity)
              .filter(([k]) => !["id", "name", "entity_type", "description", "latitude", "longitude"].includes(k))
              .slice(0, 15)
              .map(([k, v]) => (
                <div key={k} className="flex items-center justify-between text-xs py-1 border-b border-white/5">
                  <span className="text-text-muted">{k}</span>
                  <span className="text-text-secondary font-mono truncate max-w-[160px]">{String(v)}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Alert Ticker */}
      {alerts.length > 0 && (
        <div className="absolute bottom-0 left-0 right-0 z-10 h-10 bg-bg-surface/90 backdrop-blur border-t border-white/5 flex items-center overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 shrink-0 border-r border-white/5">
            <AlertTriangle size={12} className="text-accent-amber" />
            <span className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">Alerts</span>
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="flex items-center gap-8 animate-ticker whitespace-nowrap">
              {alerts.map((a, i) => (
                <span key={i} className="flex items-center gap-2 text-xs">
                  <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-semibold border", severityBg(a.severity))}>
                    {a.severity}
                  </span>
                  <span className="text-text-secondary">{a.title}</span>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Map Component ---------- */
function MapView({
  viewState,
  onViewStateChange,
  entities,
  onEntityClick,
  ready,
  onHover,
}: {
  viewState: Record<string, number>;
  onViewStateChange: (vs: Record<string, number>) => void;
  entities: Entity[];
  hotspots: unknown[];
  density: unknown[];
  onEntityClick: (info: { object?: Entity }) => void;
  ready: boolean;
  onHover?: (lat: number | null, lng: number | null) => void;
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [mapInstance, setMapInstance] = useState<unknown>(null);

  useEffect(() => {
    if (!mapRef.current || !ready) return;

    Promise.all([
      import("maplibre-gl"),
      import("@deck.gl/core"),
      import("@deck.gl/layers"),
      import("@deck.gl/geo-layers"),
    ]).then(([maplibregl]) => {
      const map = new maplibregl.Map({
        container: mapRef.current!,
        style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        center: [viewState.longitude, viewState.latitude],
        zoom: viewState.zoom,
        pitch: viewState.pitch,
        bearing: viewState.bearing,
        attributionControl: false,
      });

      if (onHover) {
        map.on("mousemove", (e) => onHover(e.lngLat.lat, e.lngLat.lng));
        map.on("mouseout", () => onHover(null, null));
      }

      map.on("move", () => {
        const center = map.getCenter();
        onViewStateChange({
          longitude: center.lng,
          latitude: center.lat,
          zoom: map.getZoom(),
          pitch: map.getPitch(),
          bearing: map.getBearing(),
        });
      });

      map.on("load", () => setMapInstance(map));
      return () => map.remove();
    }).catch(console.error);
  }, [ready]);

  useEffect(() => {
    if (!mapInstance) return;
    const map = mapInstance as import("maplibre-gl").Map;

    import("@deck.gl/mapbox").then(({ MapboxOverlay }) => {
      import("@deck.gl/layers").then(({ ScatterplotLayer }) => {
        const scatterLayer = new ScatterplotLayer({
          id: "entities",
          data: entities,
          getPosition: (d: Entity) => [d.longitude, d.latitude],
          getFillColor: (d: Entity) => entityColor(d.entity_type),
          getRadius: 8000,
          radiusMinPixels: 3,
          radiusMaxPixels: 15,
          pickable: true,
          onClick: onEntityClick,
          opacity: 0.8,
        });

        const overlay = new MapboxOverlay({ layers: [scatterLayer] });

        try {
          const ctrls = (map as unknown as { _controls: unknown[] })._controls;
          const existing = ctrls?.find((c: unknown) => c instanceof MapboxOverlay);
          if (existing) map.removeControl(existing as maplibregl.IControl);
        } catch { /* empty */ }

        map.addControl(overlay as unknown as import("maplibre-gl").IControl);
      });
    }).catch(console.error);
  }, [mapInstance, entities, onEntityClick]);

  return (
    <div ref={mapRef} className="absolute inset-0" style={{ background: "#0A0E17" }}>
      {!mapInstance && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-accent-cyan/30 border-t-accent-cyan rounded-full animate-spin" />
            <span className="text-sm text-text-muted">Loading ocean data...</span>
          </div>
        </div>
      )}
    </div>
  );
}

import type maplibregl from "maplibre-gl";
