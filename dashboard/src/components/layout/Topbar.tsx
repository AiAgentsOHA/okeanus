"use client";

import { useEffect, useState } from "react";
import { Search, Activity, AlertTriangle, Database } from "lucide-react";
import { useStore } from "@/lib/store";

export function Topbar() {
  const setSearchOpen = useStore((s) => s.setSearchOpen);
  const [stats, setStats] = useState({ entities: 0, alerts: 0, sources: 0 });

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/entities/distribution")
        .then((r) => r.json())
        .then((d: unknown[]) =>
          d.reduce(
            (sum: number, x: Record<string, unknown>) =>
              sum + ((x.count as number) || 0),
            0
          )
        )
        .catch(() => 0),
      fetch("/api/alerts?limit=1000")
        .then((r) => r.json())
        .then((d: unknown[]) => d.length)
        .catch(() => 0),
      fetch("/api/lineage/sources")
        .then((r) => r.json())
        .then((d: unknown[]) => d.length)
        .catch(() => 0),
    ]).then(([entities, alerts, sources]) =>
      setStats({ entities, alerts, sources })
    );
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [setSearchOpen]);

  return (
    <header className="h-12 bg-bg-surface border-b border-white/5 flex items-center px-4 gap-4 shrink-0">
      {/* Brand */}
      <h1 className="text-sm font-semibold tracking-wider uppercase bg-gradient-to-r from-accent-cyan to-accent-blue bg-clip-text text-transparent">
        Okeanus
      </h1>
      <span className="text-[10px] text-text-muted font-mono border border-white/10 rounded px-1.5 py-0.5">
        Ocean Intelligence
      </span>

      {/* Search trigger */}
      <button
        onClick={() => setSearchOpen(true)}
        className="ml-auto flex items-center gap-2 text-text-muted hover:text-text-secondary bg-bg-deep border border-white/10 rounded-lg px-3 py-1.5 text-xs transition-colors"
      >
        <Search size={14} />
        <span>Search entities...</span>
        <kbd className="ml-4 text-[10px] bg-bg-hover px-1.5 py-0.5 rounded font-mono">
          Cmd+K
        </kbd>
      </button>

      {/* Live stats */}
      <div className="flex items-center gap-4 ml-4">
        <div className="flex items-center gap-1.5 text-xs">
          <Database size={12} className="text-accent-cyan" />
          <span className="font-mono text-text-secondary">
            {stats.entities.toLocaleString()}
          </span>
          <span className="text-text-muted">entities</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <AlertTriangle size={12} className="text-accent-amber" />
          <span className="font-mono text-text-secondary">{stats.alerts}</span>
          <span className="text-text-muted">alerts</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Activity size={12} className="text-accent-emerald" />
          <span className="font-mono text-text-secondary">{stats.sources}</span>
          <span className="text-text-muted">sources</span>
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-accent-emerald animate-pulse" />
          <span className="text-[10px] text-text-muted uppercase tracking-wider">
            Live
          </span>
        </div>
      </div>
    </header>
  );
}
