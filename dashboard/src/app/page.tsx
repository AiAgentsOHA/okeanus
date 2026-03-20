"use client";

import { useEffect, useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { entityColor, entityColorHex, severityBg, cn } from "@/lib/utils";
import {
  Layers,
  X,
  MapPin,
  ChevronRight,
  Eye,
  EyeOff,
  AlertTriangle,
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

export default function GlobePage() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [hotspots, setHotspots] = useState<unknown[]>([]);
  const [density, setDensity] = useState<unknown[]>([]);
  const [mapReady, setMapReady] = useState(false);
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
    // Fetch entities from density endpoint (contains geo data)
    fetch("/api/analytics/entities/density")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setEntities(d);
      })
      .catch(() => {});

    fetch("/api/alerts?limit=20")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setAlerts(d);
      })
      .catch(() => {});

    fetch("/api/analytics/hotspots")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setHotspots(d);
      })
      .catch(() => {});

    fetch("/api/analytics/density")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setDensity(d);
      })
      .catch(() => {});

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
      {/* Map Container */}
      <MapView
        viewState={viewState}
        onViewStateChange={setViewState}
        entities={layers.entities ? entities : []}
        hotspots={layers.hotspots ? hotspots : []}
        density={layers.density ? density : []}
        onEntityClick={onMapClick}
        ready={mapReady}
      />

      {/* Layer Controls - Left */}
      <div className="absolute top-4 left-4 z-10">
        <button
          onClick={() => setLayerPanelOpen(!layerPanelOpen)}
          className="glass rounded-xl p-2.5 text-text-secondary hover:text-text-primary transition-colors"
        >
          <Layers size={18} />
        </button>
        {layerPanelOpen && (
          <div className="glass rounded-xl mt-2 p-3 w-48 animate-fade-in">
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
              Map Layers
            </div>
            {layerDefs.map((l) => (
              <button
                key={l.key}
                onClick={() => toggleLayer(l.key)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-bg-hover transition-colors text-left"
              >
                {layers[l.key] ? (
                  <Eye size={14} className="text-text-secondary" />
                ) : (
                  <EyeOff size={14} className="text-text-muted" />
                )}
                <div className={cn("w-2 h-2 rounded-full", l.color)} />
                <span
                  className={cn(
                    "text-xs",
                    layers[l.key] ? "text-text-primary" : "text-text-muted"
                  )}
                >
                  {l.label}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Entity Detail - Right */}
      {selectedEntity && (
        <div className="absolute top-4 right-4 bottom-16 w-80 z-10 glass rounded-xl p-4 overflow-y-auto animate-slide-in-right">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor: entityColorHex(
                    (selectedEntity.entity_type as string) || ""
                  ),
                }}
              />
              <span className="text-[10px] font-mono uppercase text-text-muted">
                {(selectedEntity.entity_type as string) || "Entity"}
              </span>
            </div>
            <button
              onClick={() => setSelectedEntity(null)}
              className="text-text-muted hover:text-text-primary"
            >
              <X size={16} />
            </button>
          </div>
          <h3 className="text-lg font-semibold mb-2">
            {(selectedEntity.name as string) || "Unknown"}
          </h3>
          {selectedEntity.description && (
            <p className="text-sm text-text-secondary mb-4 leading-relaxed">
              {selectedEntity.description as string}
            </p>
          )}
          {selectedEntity.latitude && (
            <div className="flex items-center gap-1.5 text-xs text-text-muted mb-4">
              <MapPin size={12} />
              <span className="font-mono">
                {Number(selectedEntity.latitude).toFixed(4)},{" "}
                {Number(selectedEntity.longitude).toFixed(4)}
              </span>
            </div>
          )}
          {/* Properties */}
          <div className="space-y-1.5">
            <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-1">
              Properties
            </div>
            {Object.entries(selectedEntity)
              .filter(
                ([k]) =>
                  !["id", "name", "entity_type", "description", "latitude", "longitude"].includes(k)
              )
              .slice(0, 15)
              .map(([k, v]) => (
                <div
                  key={k}
                  className="flex items-center justify-between text-xs py-1 border-b border-white/5"
                >
                  <span className="text-text-muted">{k}</span>
                  <span className="text-text-secondary font-mono truncate max-w-[160px]">
                    {String(v)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Alert Ticker - Bottom */}
      {alerts.length > 0 && (
        <div className="absolute bottom-0 left-0 right-0 z-10 h-10 bg-bg-surface/90 backdrop-blur border-t border-white/5 flex items-center overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 shrink-0 border-r border-white/5">
            <AlertTriangle size={12} className="text-accent-amber" />
            <span className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">
              Alerts
            </span>
          </div>
          <div className="flex-1 overflow-hidden">
            <div className="flex items-center gap-8 animate-ticker whitespace-nowrap">
              {alerts.map((a, i) => (
                <span key={i} className="flex items-center gap-2 text-xs">
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded text-[10px] font-semibold border",
                      severityBg(a.severity)
                    )}
                  >
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

/* ---------- Map Component (deck.gl + maplibre) ---------- */
function MapView({
  viewState,
  onViewStateChange,
  entities,
  hotspots,
  density,
  onEntityClick,
  ready,
}: {
  viewState: Record<string, number>;
  onViewStateChange: (vs: Record<string, number>) => void;
  entities: Entity[];
  hotspots: unknown[];
  density: unknown[];
  onEntityClick: (info: { object?: Entity }) => void;
  ready: boolean;
}) {
  const mapRef = useRef<HTMLDivElement>(null);
  const [DeckGL, setDeckGL] = useState<unknown>(null);
  const [mapInstance, setMapInstance] = useState<unknown>(null);

  useEffect(() => {
    if (!mapRef.current || !ready) return;

    // Dynamic imports for client-side only
    Promise.all([
      import("maplibre-gl"),
      import("@deck.gl/core"),
      import("@deck.gl/layers"),
      import("@deck.gl/geo-layers"),
    ]).then(([maplibregl, deckCore, deckLayers]) => {
      const map = new maplibregl.Map({
        container: mapRef.current!,
        style:
          "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        center: [viewState.longitude, viewState.latitude],
        zoom: viewState.zoom,
        pitch: viewState.pitch,
        bearing: viewState.bearing,
        attributionControl: false,
      });

      map.on("load", () => {
        setMapInstance(map);
      });

      return () => map.remove();
    }).catch(console.error);
  }, [ready]);

  // Update layers when data changes
  useEffect(() => {
    if (!mapInstance) return;
    const map = mapInstance as import("maplibre-gl").Map;

    import("@deck.gl/mapbox").then(({ MapboxOverlay }) => {
      import("@deck.gl/layers").then(({ ScatterplotLayer }) => {
        // Remove existing overlay
        const existingLayers = map.getStyle()?.layers || [];

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

        const overlay = new MapboxOverlay({
          layers: [scatterLayer],
        });

        // Check if overlay already exists and remove it
        try {
          const ctrls = (map as unknown as { _controls: unknown[] })._controls;
          const existing = ctrls?.find((c: unknown) => c instanceof MapboxOverlay);
          if (existing) map.removeControl(existing as maplibregl.IControl);
        } catch {}

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

import { useRef } from "react";
import type maplibregl from "maplibre-gl";
