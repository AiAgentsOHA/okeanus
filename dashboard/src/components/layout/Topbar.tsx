"use client";

import { useEffect, useState, useRef } from "react";
import { Search, Activity, AlertTriangle, Database } from "lucide-react";
import { useStore } from "@/lib/store";

function AnimatedCounter({ value, label }: { value: number; label: string }) {
  const [display, setDisplay] = useState(0);
  const prevRef = useRef(0);

  useEffect(() => {
    if (value === 0) return;
    const start = prevRef.current;
    const end = value;
    const duration = 800;
    const startTime = performance.now();

    function animate(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(start + (end - start) * eased));
      if (progress < 1) requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
    prevRef.current = end;
  }, [value]);

  return (
    <span className="font-mono text-text-secondary stat-counter">
      {display.toLocaleString()}
    </span>
  );
}

function UTCClock() {
  const [time, setTime] = useState("");

  useEffect(() => {
    function tick() {
      const now = new Date();
      setTime(
        now.toUTCString().slice(17, 25) // HH:MM:SS
      );
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-bg-deep border border-white/5">
      <span className="text-[10px] text-text-muted uppercase tracking-wider">UTC</span>
      <span className="font-mono text-xs text-accent-cyan tabular-nums">{time}</span>
    </div>
  );
}

export function Topbar() {
  const setSearchOpen = useStore((s) => s.setSearchOpen);
  const [stats, setStats] = useState({ entities: 0, alerts: 0, sources: 0 });

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/entities/distribution")
        .then((r) => r.json())
        .then((d: { count?: number }[]) =>
          d.reduce(
            (sum: number, x: { count?: number }) =>
              sum + (x.count || 0),
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
      {/* Brand — Okeanus Logo Treatment */}
      <div className="flex items-center gap-2.5">
        <h1 className="text-sm font-bold tracking-[0.2em] uppercase bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet bg-clip-text text-transparent">
          Okeanus
        </h1>
        <span className="text-[10px] text-text-muted font-mono border border-white/10 rounded px-1.5 py-0.5 bg-bg-deep/50">
          Ocean Intelligence
        </span>
      </div>

      {/* Search trigger */}
      <button
        onClick={() => setSearchOpen(true)}
        className="ml-auto flex items-center gap-2 text-text-muted hover:text-text-secondary bg-bg-deep border border-white/10 rounded-lg px-3 py-1.5 text-xs transition-all hover:border-accent-cyan/30 hover:shadow-[0_0_12px_rgba(6,182,212,0.1)]"
      >
        <Search size={14} />
        <span>Search entities...</span>
        <kbd className="ml-4 text-[10px] bg-bg-hover px-1.5 py-0.5 rounded font-mono">
          Cmd+K
        </kbd>
      </button>

      {/* Live stats with animated counters */}
      <div className="flex items-center gap-4 ml-4">
        <div className="flex items-center gap-1.5 text-xs">
          <Database size={12} className="text-accent-cyan" />
          <AnimatedCounter value={stats.entities} label="entities" />
          <span className="text-text-muted">entities</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <AlertTriangle size={12} className="text-accent-amber" />
          <AnimatedCounter value={stats.alerts} label="alerts" />
          <span className="text-text-muted">alerts</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <Activity size={12} className="text-accent-emerald" />
          <AnimatedCounter value={stats.sources} label="sources" />
          <span className="text-text-muted">sources</span>
        </div>

        {/* Separator */}
        <div className="w-px h-5 bg-white/10" />

        {/* UTC Clock */}
        <UTCClock />

        {/* LIVE indicator with pulsing ring */}
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-accent-emerald/10 border border-accent-emerald/20">
          <div className="relative w-2 h-2">
            <div className="absolute inset-0 rounded-full bg-accent-emerald" />
            <div className="live-dot absolute inset-0 rounded-full bg-accent-emerald" />
          </div>
          <span className="text-[10px] text-accent-emerald font-semibold uppercase tracking-wider">
            Live
          </span>
        </div>
      </div>
    </header>
  );
}
