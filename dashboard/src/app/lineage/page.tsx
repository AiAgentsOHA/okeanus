"use client";

import { useEffect, useState } from "react";
import { GitBranch, Database, ArrowRight, Layers, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

interface Source {
  source_name: string;
  adapter_type: string;
  observation_count: number;
  entity_count: number;
  last_run?: string;
}

const PIPELINE_STAGES = [
  { label: "Sources", icon: Database, color: "bg-accent-cyan", desc: "Raw data ingestion from APIs, feeds, databases" },
  { label: "Adapters", icon: Layers, color: "bg-accent-blue", desc: "Normalize & validate into observations" },
  { label: "Observations", icon: Eye, color: "bg-accent-emerald", desc: "Structured records with geo/temporal data" },
  { label: "Transform", icon: GitBranch, color: "bg-accent-amber", desc: "Entity resolution, dedup, enrichment" },
  { label: "Entities", icon: Database, color: "bg-accent-violet", desc: "Knowledge graph nodes with relationships" },
];

export default function LineagePage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Source | null>(null);

  useEffect(() => {
    fetch("/api/lineage/sources")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setSources(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const totalObs = sources.reduce((s, d) => s + (d.observation_count || 0), 0);
  const totalEntities = sources.reduce((s, d) => s + (d.entity_count || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-emerald/30 border-t-accent-emerald rounded-full animate-spin" />
          <span className="text-sm text-text-muted">Loading lineage data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Data Lineage</h1>
        <p className="text-sm text-text-muted">End-to-end data provenance and pipeline transparency</p>
      </div>

      {/* Pipeline Flow Diagram */}
      <div className="bg-bg-surface border border-white/5 rounded-xl p-6 mb-6">
        <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-4">
          Pipeline Flow
        </div>
        <div className="flex items-center justify-between gap-2">
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage.label} className="flex items-center gap-2 flex-1">
              <div className="flex flex-col items-center gap-2 flex-1">
                <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", stage.color)}>
                  <stage.icon size={20} className="text-white" />
                </div>
                <span className="text-xs font-semibold text-text-primary">{stage.label}</span>
                <span className="text-[10px] text-text-muted text-center leading-tight max-w-[120px]">
                  {stage.desc}
                </span>
                {i === 0 && (
                  <span className="font-mono text-xs text-accent-cyan mt-1">
                    {sources.length} active
                  </span>
                )}
                {i === 2 && (
                  <span className="font-mono text-xs text-accent-emerald mt-1">
                    {totalObs.toLocaleString()}
                  </span>
                )}
                {i === 4 && (
                  <span className="font-mono text-xs text-accent-violet mt-1">
                    {totalEntities.toLocaleString()}
                  </span>
                )}
              </div>
              {i < PIPELINE_STAGES.length - 1 && (
                <ArrowRight size={16} className="text-text-muted shrink-0 mt-[-30px]" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Source Coverage Table */}
      <div className="bg-bg-surface border border-white/5 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-white/5">
          <span className="text-xs font-semibold text-text-secondary">
            Source Coverage ({sources.length} sources)
          </span>
        </div>
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/5">
              <th className="text-left text-[10px] uppercase tracking-wider text-text-muted font-semibold px-4 py-2.5">
                Source Name
              </th>
              <th className="text-left text-[10px] uppercase tracking-wider text-text-muted font-semibold px-4 py-2.5">
                Adapter Type
              </th>
              <th className="text-right text-[10px] uppercase tracking-wider text-text-muted font-semibold px-4 py-2.5">
                Observations
              </th>
              <th className="text-right text-[10px] uppercase tracking-wider text-text-muted font-semibold px-4 py-2.5">
                Entities
              </th>
              <th className="text-right text-[10px] uppercase tracking-wider text-text-muted font-semibold px-4 py-2.5">
                Last Run
              </th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s, i) => (
              <tr
                key={s.source_name || i}
                onClick={() => setSelected(selected?.source_name === s.source_name ? null : s)}
                className={cn(
                  "border-b border-white/[0.03] cursor-pointer transition-colors",
                  selected?.source_name === s.source_name
                    ? "bg-bg-hover"
                    : "hover:bg-bg-hover/50"
                )}
              >
                <td className="px-4 py-3 text-sm text-text-primary">{s.source_name}</td>
                <td className="px-4 py-3">
                  <span className="text-xs font-mono bg-bg-deep px-2 py-0.5 rounded text-text-muted">
                    {s.adapter_type}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-accent-emerald">
                  {(s.observation_count || 0).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-accent-violet">
                  {(s.entity_count || 0).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-right font-mono text-xs text-text-muted">
                  {s.last_run ? new Date(s.last_run).toLocaleDateString() : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Selected source detail */}
      {selected && (
        <div className="mt-4 bg-bg-surface border border-white/5 rounded-xl p-4 animate-fade-in">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold">{selected.source_name}</h3>
            <span className="text-xs font-mono bg-bg-deep px-2 py-0.5 rounded text-text-muted">
              {selected.adapter_type}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Observations</div>
              <div className="text-xl font-bold font-mono text-accent-emerald">
                {(selected.observation_count || 0).toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Entities</div>
              <div className="text-xl font-bold font-mono text-accent-violet">
                {(selected.entity_count || 0).toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1">Conversion Rate</div>
              <div className="text-xl font-bold font-mono text-accent-cyan">
                {selected.observation_count > 0
                  ? ((selected.entity_count / selected.observation_count) * 100).toFixed(1)
                  : "0"}
                %
              </div>
            </div>
          </div>
          {/* Pipeline visualization for this source */}
          <div className="mt-4 flex items-center gap-3 text-xs">
            <span className="bg-accent-cyan/20 text-accent-cyan px-2 py-1 rounded font-mono">
              {selected.source_name}
            </span>
            <ArrowRight size={12} className="text-text-muted" />
            <span className="bg-accent-blue/20 text-accent-blue px-2 py-1 rounded font-mono">
              {selected.adapter_type}
            </span>
            <ArrowRight size={12} className="text-text-muted" />
            <span className="bg-accent-emerald/20 text-accent-emerald px-2 py-1 rounded font-mono">
              {(selected.observation_count || 0).toLocaleString()} obs
            </span>
            <ArrowRight size={12} className="text-text-muted" />
            <span className="bg-accent-violet/20 text-accent-violet px-2 py-1 rounded font-mono">
              {(selected.entity_count || 0).toLocaleString()} entities
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
