"use client";

import { useState } from "react";
import {
  Database,
  GitBranch,
  Network,
  Users,
  Lightbulb,
  Brain,
  ChevronRight,
  ChevronDown,
  Search,
  ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DecisionTree as DecisionTreeType, getDecisionTree } from "@/lib/api";

/* ---------- layer icon/color mapping ---------- */
const LAYER_META: Record<string, { icon: typeof Database; color: string; bg: string }> = {
  data_lineage: { icon: GitBranch, color: "text-accent-cyan", bg: "bg-accent-cyan/10" },
  knowledge_graph: { icon: Network, color: "text-accent-blue", bg: "bg-accent-blue/10" },
  community: { icon: Users, color: "text-accent-violet", bg: "bg-accent-violet/10" },
  insights: { icon: Lightbulb, color: "text-accent-amber", bg: "bg-accent-amber/10" },
};

/* ---------- sub-components ---------- */

function LineageNodes({ nodes, edges }: { nodes: unknown[]; edges: unknown[] }) {
  const n = nodes as { id: string; node_type: string; name: string; source_name?: string }[];
  if (!n.length) return <span className="text-xs text-text-muted italic">No lineage data yet (run ingest with lineage tracking enabled)</span>;

  return (
    <div className="space-y-1">
      {n.map((node) => (
        <div key={node.id} className="flex items-center gap-2 text-xs">
          <span className={cn(
            "px-1.5 py-0.5 rounded font-mono text-[10px]",
            node.node_type === "SOURCE" ? "bg-accent-cyan/20 text-accent-cyan" :
            node.node_type === "ADAPTER" ? "bg-accent-blue/20 text-accent-blue" :
            "bg-accent-emerald/20 text-accent-emerald"
          )}>
            {node.node_type}
          </span>
          <span className="text-text-primary truncate">{node.name}</span>
        </div>
      ))}
    </div>
  );
}

function KnowledgeEdges({ edges }: { edges: { edge_type: string; strength: number; source_label: string; target_label: string; evidence_type: string }[] }) {
  if (!edges.length) return <span className="text-xs text-text-muted italic">No knowledge graph connections</span>;

  return (
    <div className="space-y-1.5">
      {edges.slice(0, 15).map((e, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="text-text-primary truncate max-w-[140px]">{e.source_label}</span>
          <span className="flex items-center gap-1 shrink-0">
            <ArrowRight size={10} className="text-text-muted" />
            <span className="font-mono text-[10px] bg-accent-blue/15 text-accent-blue px-1.5 py-0.5 rounded">
              {e.edge_type}
            </span>
            <ArrowRight size={10} className="text-text-muted" />
          </span>
          <span className="text-text-primary truncate max-w-[140px]">{e.target_label}</span>
          <span className="font-mono text-[10px] text-text-muted ml-auto">
            {e.strength?.toFixed(2)}
          </span>
        </div>
      ))}
      {edges.length > 15 && (
        <span className="text-[10px] text-text-muted">+ {edges.length - 15} more edges</span>
      )}
    </div>
  );
}

function CommunityInfo({ community }: { community: { community_id: number; size: number; pagerank?: number; centrality?: number } | null }) {
  if (!community) return <span className="text-xs text-text-muted italic">Not assigned to any community (run NetworkX rebuild)</span>;

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <div className="text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Community</div>
        <div className="font-mono text-sm font-bold text-accent-violet">#{community.community_id}</div>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Members</div>
        <div className="font-mono text-sm font-bold text-text-primary">{community.size}</div>
      </div>
      {community.pagerank != null && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-text-muted mb-0.5">PageRank</div>
          <div className="font-mono text-sm text-text-primary">{community.pagerank.toExponential(2)}</div>
        </div>
      )}
      {community.centrality != null && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-text-muted mb-0.5">Centrality</div>
          <div className="font-mono text-sm text-text-primary">{community.centrality.toFixed(4)}</div>
        </div>
      )}
    </div>
  );
}

function InsightsList({ insights }: { insights: DecisionTreeType["layers"][0]["insights"] }) {
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null);

  if (!insights?.length) return <span className="text-xs text-text-muted italic">No insights generated yet (run insight generation)</span>;

  return (
    <div className="space-y-3">
      {insights.map((ins) => (
        <div key={ins.id} className="border border-white/5 rounded-lg p-3 bg-bg-deep/50">
          <div className="flex items-start justify-between gap-2 mb-1">
            <span className="text-xs font-semibold text-text-primary leading-tight">{ins.title}</span>
            <span className={cn(
              "text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0",
              ins.confidence >= 0.7 ? "bg-accent-emerald/20 text-accent-emerald" :
              ins.confidence >= 0.5 ? "bg-accent-amber/20 text-accent-amber" :
              "bg-accent-red/20 text-accent-red"
            )}>
              {(ins.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-mono bg-bg-surface px-1.5 py-0.5 rounded text-text-muted">
              {ins.insight_type}
            </span>
            <span className="text-[10px] text-text-muted">{ins.generator}</span>
          </div>
          <p className="text-xs text-text-secondary leading-relaxed mb-2">{ins.description}</p>

          {/* Reasoning Traces */}
          {ins.reasoning_traces.length > 0 && (
            <div>
              <button
                onClick={() => setExpandedTrace(expandedTrace === ins.id ? null : ins.id)}
                className="flex items-center gap-1 text-[10px] text-accent-amber hover:text-accent-amber/80 transition-colors"
              >
                <Brain size={10} />
                {expandedTrace === ins.id ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
                {ins.reasoning_traces.length} reasoning trace{ins.reasoning_traces.length > 1 ? "s" : ""}
              </button>
              {expandedTrace === ins.id && (
                <div className="mt-2 space-y-2 pl-3 border-l border-accent-amber/20">
                  {ins.reasoning_traces.map((trace) => (
                    <div key={trace.id} className="text-xs">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="font-mono text-[10px] bg-accent-amber/15 text-accent-amber px-1 py-0.5 rounded">
                          {trace.phase}
                        </span>
                      </div>
                      <div className="text-text-muted leading-relaxed">
                        <span className="font-semibold text-text-secondary">In: </span>
                        {trace.input_text}
                      </div>
                      <div className="text-text-secondary leading-relaxed mt-0.5">
                        <span className="font-semibold">Out: </span>
                        {trace.output_text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ---------- main component ---------- */

export default function DecisionTreeView() {
  const [entityId, setEntityId] = useState("");
  const [tree, setTree] = useState<DecisionTreeType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const handleSearch = async () => {
    if (!entityId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getDecisionTree(entityId.trim());
      if (data.error) {
        setError(data.error);
        setTree(null);
      } else {
        setTree(data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch tree");
      setTree(null);
    }
    setLoading(false);
  };

  const toggleLayer = (name: string) => {
    setCollapsed((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <div>
      {/* Search bar */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Paste entity UUID to trace provenance..."
            className="w-full pl-9 pr-3 py-2 bg-bg-deep border border-white/10 rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-cyan/50"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !entityId.trim()}
          className="px-4 py-2 bg-accent-cyan/20 text-accent-cyan text-sm font-semibold rounded-lg hover:bg-accent-cyan/30 transition-colors disabled:opacity-40"
        >
          {loading ? "Tracing..." : "Trace"}
        </button>
      </div>

      {error && (
        <div className="bg-accent-red/10 border border-accent-red/20 rounded-lg p-3 mb-4">
          <span className="text-sm text-accent-red">{error}</span>
        </div>
      )}

      {tree && (
        <div className="space-y-3">
          {/* Entity header */}
          <div className="bg-bg-surface border border-white/5 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 rounded-lg bg-accent-emerald/20 flex items-center justify-center">
                <Database size={18} className="text-accent-emerald" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-text-primary">{tree.entity?.name}</h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] font-mono bg-bg-deep px-1.5 py-0.5 rounded text-text-muted">
                    {tree.entity?.entity_type}
                  </span>
                  <span className="text-[10px] text-text-muted">from {tree.entity?.source_name}</span>
                  {tree.entity?.country && (
                    <span className="text-[10px] text-text-muted">{tree.entity.country}</span>
                  )}
                </div>
              </div>
            </div>
            {tree.entity?.lat && tree.entity?.lon && (
              <div className="text-[10px] font-mono text-text-muted">
                {tree.entity.lat.toFixed(4)}, {tree.entity.lon.toFixed(4)}
              </div>
            )}
          </div>

          {/* Provenance layers */}
          {tree.layers.map((layer) => {
            const meta = LAYER_META[layer.name] || { icon: Database, color: "text-text-muted", bg: "bg-bg-deep" };
            const Icon = meta.icon;
            const isCollapsed = collapsed[layer.name];

            return (
              <div key={layer.name} className="bg-bg-surface border border-white/5 rounded-xl overflow-hidden">
                <button
                  onClick={() => toggleLayer(layer.name)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-bg-hover/50 transition-colors"
                >
                  <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center", meta.bg)}>
                    <Icon size={14} className={meta.color} />
                  </div>
                  <span className="text-xs font-semibold text-text-primary flex-1 text-left">
                    {layer.label}
                  </span>
                  {layer.count != null && (
                    <span className="font-mono text-[10px] text-text-muted mr-2">
                      {layer.count} items
                    </span>
                  )}
                  {isCollapsed ? (
                    <ChevronRight size={14} className="text-text-muted" />
                  ) : (
                    <ChevronDown size={14} className="text-text-muted" />
                  )}
                </button>
                {!isCollapsed && (
                  <div className="px-4 pb-4 pt-1">
                    {layer.name === "data_lineage" && (
                      <LineageNodes
                        nodes={(layer.nodes as unknown[]) || []}
                        edges={(layer.edges as unknown[]) || []}
                      />
                    )}
                    {layer.name === "knowledge_graph" && (
                      <KnowledgeEdges edges={(layer.edges as any[]) || []} />
                    )}
                    {layer.name === "community" && (
                      <CommunityInfo community={layer.community || null} />
                    )}
                    {layer.name === "insights" && (
                      <InsightsList insights={layer.insights} />
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!tree && !error && !loading && (
        <div className="text-center py-12">
          <GitBranch size={32} className="text-text-muted/30 mx-auto mb-3" />
          <p className="text-sm text-text-muted">Enter an entity UUID to trace its full decision provenance</p>
          <p className="text-xs text-text-muted/60 mt-1">
            source &rarr; adapter &rarr; entity &rarr; graph &rarr; community &rarr; insight &rarr; reasoning
          </p>
        </div>
      )}
    </div>
  );
}
