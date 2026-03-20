"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Search, Filter, X, ZoomIn, ZoomOut, Maximize2 } from "lucide-react";
import { entityColorHex, cn } from "@/lib/utils";
import { useStore } from "@/lib/store";

interface GraphNode {
  id: string;
  label?: string;
  name?: string;
  entity_type?: string;
  type?: string;
  centrality?: number;
  size?: number;
  x?: number;
  y?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  edge_type?: string;
  relationship_type?: string;
  weight?: number;
}

const EDGE_TYPES = ["SPATIALLY_NEAR", "RELATES_TO", "CORRELATES_WITH", "CAUSES"];

export default function GraphPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set(EDGE_TYPES));
  const [filterOpen, setFilterOpen] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const setSelectedEntity = useStore((s) => s.setSelectedEntity);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/relationships/centrality")
        .then((r) => r.json())
        .catch(() => []),
      fetch("/api/analytics/flows/network")
        .then((r) => r.json())
        .catch(() => ({ nodes: [], edges: [] })),
    ]).then(([centrality, network]) => {
      const nodeMap = new Map<string, GraphNode>();

      // Add centrality nodes
      if (Array.isArray(centrality)) {
        centrality.forEach((n: GraphNode) => {
          nodeMap.set(n.id, { ...n, size: (n.centrality || 0.5) * 20 + 4 });
        });
      }

      // Add network nodes
      if (network.nodes && Array.isArray(network.nodes)) {
        network.nodes.forEach((n: GraphNode) => {
          if (!nodeMap.has(n.id)) {
            nodeMap.set(n.id, { ...n, size: 6 });
          }
        });
      }

      // Layout nodes in a force-directed-like circle/spiral
      const allNodes = Array.from(nodeMap.values());
      const cx = 500, cy = 400;
      allNodes.forEach((n, i) => {
        const angle = (i / allNodes.length) * Math.PI * 2 * 3; // spiral
        const r = 80 + i * 1.2;
        n.x = cx + Math.cos(angle) * r;
        n.y = cy + Math.sin(angle) * r;
      });

      setNodes(allNodes);

      // Edges
      const allEdges: GraphEdge[] = [];
      if (network.edges && Array.isArray(network.edges)) {
        network.edges.forEach((e: GraphEdge) => {
          if (nodeMap.has(e.source) && nodeMap.has(e.target)) {
            allEdges.push(e);
          }
        });
      }
      setEdges(allEdges);
      setLoading(false);
    });
  }, []);

  // Canvas rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || nodes.length === 0) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.save();
    ctx.translate(offset.x + rect.width / 2, offset.y + rect.height / 2);
    ctx.scale(zoom, zoom);
    ctx.translate(-500, -400);

    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    const filteredEdges = edges.filter((e) =>
      activeFilters.has(e.edge_type || e.relationship_type || "RELATES_TO")
    );

    // Draw edges
    ctx.lineWidth = 0.5;
    ctx.globalAlpha = 0.15;
    filteredEdges.forEach((e) => {
      const src = nodeMap.get(e.source);
      const tgt = nodeMap.get(e.target);
      if (src?.x != null && tgt?.x != null) {
        ctx.strokeStyle = "#64748B";
        ctx.beginPath();
        ctx.moveTo(src.x, src.y!);
        ctx.lineTo(tgt.x, tgt.y!);
        ctx.stroke();
      }
    });

    // Draw nodes
    ctx.globalAlpha = 1;
    const matchingIds = searchQuery
      ? new Set(
          nodes
            .filter((n) =>
              (n.name || n.label || "")
                .toLowerCase()
                .includes(searchQuery.toLowerCase())
            )
            .map((n) => n.id)
        )
      : null;

    nodes.forEach((n) => {
      if (n.x == null || n.y == null) return;
      const type = n.entity_type || n.type || "unknown";
      const color = entityColorHex(type);
      const size = n.size || 5;
      const isMatch = !matchingIds || matchingIds.has(n.id);
      const isSelected = selectedNode?.id === n.id;

      ctx.globalAlpha = isMatch ? 0.85 : 0.15;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(n.x, n.y, size, 0, Math.PI * 2);
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = "#FFFFFF";
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.fillStyle = "#F1F5F9";
        ctx.font = "11px Inter, sans-serif";
        ctx.fillText(n.name || n.label || n.id, n.x + size + 4, n.y + 4);
      }
    });

    ctx.restore();
  }, [nodes, edges, zoom, offset, activeFilters, searchQuery, selectedNode]);

  // Handle canvas click
  const handleCanvasClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left - offset.x - rect.width / 2) / zoom + 500;
      const my = (e.clientY - rect.top - offset.y - rect.height / 2) / zoom + 400;

      const clicked = nodes.find((n) => {
        if (n.x == null || n.y == null) return false;
        const dx = n.x - mx;
        const dy = n.y - my;
        return Math.sqrt(dx * dx + dy * dy) < (n.size || 5) + 4;
      });

      setSelectedNode(clicked || null);
      if (clicked) {
        setSelectedEntity(clicked as unknown as Record<string, unknown>);
      }
    },
    [nodes, zoom, offset, setSelectedEntity]
  );

  // Mouse drag
  const handleMouseDown = (e: React.MouseEvent) => {
    setDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };
  const handleMouseUp = () => setDragging(false);

  const toggleFilter = (type: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  };

  return (
    <div className="relative w-full h-full bg-bg-deep">
      {loading ? (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-accent-violet/30 border-t-accent-violet rounded-full animate-spin" />
            <span className="text-sm text-text-muted">Building knowledge graph...</span>
          </div>
        </div>
      ) : (
        <>
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full cursor-grab active:cursor-grabbing"
            onClick={handleCanvasClick}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={(e) => {
              e.preventDefault();
              setZoom((z) => Math.max(0.1, Math.min(5, z - e.deltaY * 0.001)));
            }}
          />

          {/* Controls - Top Left */}
          <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
            {/* Search */}
            <div className="glass rounded-xl flex items-center gap-2 px-3 py-2 w-64">
              <Search size={14} className="text-text-muted shrink-0" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search nodes..."
                className="bg-transparent text-xs text-text-primary outline-none flex-1 placeholder:text-text-muted"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className="text-text-muted">
                  <X size={12} />
                </button>
              )}
            </div>

            {/* Filter */}
            <button
              onClick={() => setFilterOpen(!filterOpen)}
              className="glass rounded-xl p-2.5 w-fit text-text-secondary hover:text-text-primary"
            >
              <Filter size={16} />
            </button>
            {filterOpen && (
              <div className="glass rounded-xl p-3 w-56 animate-fade-in">
                <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
                  Edge Types
                </div>
                {EDGE_TYPES.map((t) => (
                  <button
                    key={t}
                    onClick={() => toggleFilter(t)}
                    className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-bg-hover text-left"
                  >
                    <div
                      className={cn(
                        "w-3 h-3 rounded border",
                        activeFilters.has(t)
                          ? "bg-accent-blue border-accent-blue"
                          : "border-text-muted"
                      )}
                    />
                    <span className="text-xs text-text-secondary">{t}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Zoom controls - Bottom Left */}
          <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-1">
            <button
              onClick={() => setZoom((z) => Math.min(5, z + 0.3))}
              className="glass rounded-lg p-2 text-text-secondary hover:text-text-primary"
            >
              <ZoomIn size={16} />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.1, z - 0.3))}
              className="glass rounded-lg p-2 text-text-secondary hover:text-text-primary"
            >
              <ZoomOut size={16} />
            </button>
            <button
              onClick={() => {
                setZoom(1);
                setOffset({ x: 0, y: 0 });
              }}
              className="glass rounded-lg p-2 text-text-secondary hover:text-text-primary"
            >
              <Maximize2 size={16} />
            </button>
          </div>

          {/* Selected node detail - Right */}
          {selectedNode && (
            <div className="absolute top-4 right-4 w-72 z-10 glass rounded-xl p-4 animate-slide-in-right">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{
                      backgroundColor: entityColorHex(
                        selectedNode.entity_type || selectedNode.type || ""
                      ),
                    }}
                  />
                  <span className="text-[10px] font-mono uppercase text-text-muted">
                    {selectedNode.entity_type || selectedNode.type || "node"}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-text-muted hover:text-text-primary"
                >
                  <X size={14} />
                </button>
              </div>
              <h3 className="text-sm font-semibold mb-2">
                {selectedNode.name || selectedNode.label || selectedNode.id}
              </h3>
              {selectedNode.centrality != null && (
                <div className="text-xs text-text-muted mb-2">
                  Centrality:{" "}
                  <span className="font-mono text-accent-cyan">
                    {Number(selectedNode.centrality).toFixed(4)}
                  </span>
                </div>
              )}
              {/* Connected edges */}
              <div className="text-[10px] uppercase tracking-wider text-text-muted mt-3 mb-1 font-semibold">
                Connections
              </div>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {edges
                  .filter(
                    (e) =>
                      e.source === selectedNode.id ||
                      e.target === selectedNode.id
                  )
                  .slice(0, 20)
                  .map((e, i) => {
                    const otherId =
                      e.source === selectedNode.id ? e.target : e.source;
                    const other = nodes.find((n) => n.id === otherId);
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 text-xs text-text-secondary"
                      >
                        <ChevronRight size={10} className="text-text-muted" />
                        <span className="truncate">
                          {other?.name || other?.label || otherId}
                        </span>
                        <span className="text-[9px] text-text-muted font-mono ml-auto">
                          {e.edge_type || e.relationship_type || ""}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Stats overlay */}
          <div className="absolute bottom-4 right-4 z-10 glass rounded-xl px-3 py-2 flex items-center gap-4 text-xs">
            <span className="text-text-muted">
              Nodes:{" "}
              <span className="font-mono text-text-secondary">{nodes.length.toLocaleString()}</span>
            </span>
            <span className="text-text-muted">
              Edges:{" "}
              <span className="font-mono text-text-secondary">{edges.length.toLocaleString()}</span>
            </span>
            <span className="text-text-muted">
              Zoom: <span className="font-mono text-text-secondary">{zoom.toFixed(1)}x</span>
            </span>
          </div>

          {/* Legend */}
          <div className="absolute top-4 right-4 z-[5] glass rounded-xl p-3">
            <div className="text-[10px] uppercase tracking-wider text-text-muted mb-2 font-semibold">
              Entity Types
            </div>
            {["species", "infrastructure", "region", "event", "assessment", "flow"].map((t) => (
              <div key={t} className="flex items-center gap-2 py-0.5">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: entityColorHex(t) }}
                />
                <span className="text-[10px] text-text-secondary capitalize">{t}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
