"use client";

import { useEffect, useState, useRef, useMemo } from "react";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  X,
  Filter,
  Clock,
  BarChart2,
  Volume2,
  VolumeX,
  List,
} from "lucide-react";
import { severityBg, cn } from "@/lib/utils";

interface Alert {
  id?: string;
  severity: string;
  title: string;
  description: string;
  alert_type?: string;
  created_at?: string;
  payload?: Record<string, unknown>;
}

type SortKey = "severity" | "title" | "alert_type" | "created_at";
type ViewMode = "table" | "timeline";

const SEV_ORDER: Record<string, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

const SEV_COLORS: Record<string, string> = {
  CRITICAL: "#EF4444",
  HIGH: "#F59E0B",
  MEDIUM: "#3B82F6",
  LOW: "#64748B",
};

/* ===== Severity Trend Sparkline ===== */
function SeveritySparkline({ alerts }: { alerts: Alert[] }) {
  const bins = useMemo(() => {
    const now = Date.now();
    const dayMs = 86400000;
    const days: Record<string, Record<string, number>> = {};

    for (let i = 13; i >= 0; i--) {
      const d = new Date(now - i * dayMs).toISOString().slice(0, 10);
      days[d] = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0 };
    }

    alerts.forEach((a) => {
      if (!a.created_at) return;
      const day = a.created_at.slice(0, 10);
      if (days[day]) {
        days[day][a.severity] = (days[day][a.severity] || 0) + 1;
      }
    });

    return Object.entries(days).map(([date, counts]) => ({
      date,
      ...counts,
      total: Object.values(counts).reduce((s, c) => s + c, 0),
    }));
  }, [alerts]);

  const maxTotal = Math.max(...bins.map((b) => b.total), 1);

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-bg-deep/50 rounded-xl border border-white/5">
      <BarChart2 size={14} className="text-text-muted shrink-0" />
      <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold shrink-0">
        14-Day Trend
      </div>
      <div className="flex items-end gap-[2px] h-6 flex-1 justify-end">
        {bins.map((bin, i) => (
          <div
            key={i}
            className="flex flex-col-reverse gap-[1px]"
            title={`${bin.date}: ${bin.total} alerts`}
          >
            {(["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const).map((sev) => {
              const count = (bin as unknown as Record<string, number>)[sev] || 0;
              if (count === 0) return null;
              return (
                <div
                  key={sev}
                  className="sparkline-bar"
                  style={{
                    height: `${Math.max((count / maxTotal) * 24, 2)}px`,
                    backgroundColor: SEV_COLORS[sev],
                    opacity: 0.8,
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ===== Timeline View ===== */
function TimelineView({
  alerts,
  onSelect,
  selected,
}: {
  alerts: Alert[];
  onSelect: (a: Alert) => void;
  selected: Alert | null;
}) {
  const grouped = useMemo(() => {
    const groups: Record<string, Alert[]> = {};
    alerts.forEach((a) => {
      const date = a.created_at
        ? new Date(a.created_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        : "Unknown Date";
      if (!groups[date]) groups[date] = [];
      groups[date].push(a);
    });
    return Object.entries(groups);
  }, [alerts]);

  return (
    <div className="flex-1 overflow-y-auto pr-2 space-y-6">
      {grouped.map(([date, dateAlerts]) => (
        <div key={date}>
          <div className="flex items-center gap-3 mb-3">
            <Clock size={12} className="text-text-muted" />
            <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
              {date}
            </span>
            <div className="flex-1 h-px bg-white/5" />
            <span className="text-[10px] font-mono text-text-muted">
              {dateAlerts.length}
            </span>
          </div>
          <div className="space-y-2 ml-6 border-l border-white/5 pl-4">
            {dateAlerts.map((a, i) => (
              <div
                key={a.id || i}
                onClick={() => onSelect(a)}
                className={cn(
                  "relative p-3 rounded-lg cursor-pointer transition-all duration-200 card-glow border border-transparent",
                  selected?.id === a.id
                    ? "bg-bg-hover border-accent-cyan/20"
                    : "bg-bg-surface/50 hover:bg-bg-hover/50",
                  a.severity === "CRITICAL" && "critical-flash"
                )}
              >
                <div
                  className="absolute -left-[21px] top-4 w-2.5 h-2.5 rounded-full border-2 border-bg-deep"
                  style={{ backgroundColor: SEV_COLORS[a.severity] || "#64748B" }}
                />
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          "inline-flex px-1.5 py-0.5 rounded text-[9px] font-semibold border",
                          severityBg(a.severity)
                        )}
                      >
                        {a.severity}
                      </span>
                      <span className="text-[10px] font-mono text-text-muted">
                        {a.alert_type || "general"}
                      </span>
                    </div>
                    <p className="text-sm text-text-primary truncate">{a.title}</p>
                  </div>
                  {a.created_at && (
                    <span className="text-[10px] font-mono text-text-muted shrink-0">
                      {new Date(a.created_at).toLocaleTimeString("en-US", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("severity");
  const [sortAsc, setSortAsc] = useState(true);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [filterSev, setFilterSev] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [newCritical, setNewCritical] = useState(false);
  const prevCountRef = useRef(0);

  useEffect(() => {
    fetch("/api/alerts?limit=200")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) {
          setAlerts(d);
          const critCount = d.filter(
            (a: Alert) => a.severity === "CRITICAL"
          ).length;
          if (prevCountRef.current > 0 && critCount > prevCountRef.current) {
            setNewCritical(true);
            if (soundEnabled) {
              try {
                const ctx = new AudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 800;
                gain.gain.value = 0.1;
                osc.start();
                osc.stop(ctx.currentTime + 0.15);
                setTimeout(() => {
                  const osc2 = ctx.createOscillator();
                  const gain2 = ctx.createGain();
                  osc2.connect(gain2);
                  gain2.connect(ctx.destination);
                  osc2.frequency.value = 1000;
                  gain2.gain.value = 0.1;
                  osc2.start();
                  osc2.stop(ctx.currentTime + 0.15);
                }, 200);
              } catch { /* empty */ }
            }
            setTimeout(() => setNewCritical(false), 3000);
          }
          prevCountRef.current = critCount;
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [soundEnabled]);

  const sorted = [...alerts]
    .filter((a) => !filterSev || a.severity === filterSev)
    .sort((a, b) => {
      let cmp = 0;
      if (sortKey === "severity") {
        cmp = (SEV_ORDER[a.severity] ?? 9) - (SEV_ORDER[b.severity] ?? 9);
      } else {
        const av = (a[sortKey] as string) || "";
        const bv = (b[sortKey] as string) || "";
        cmp = av.localeCompare(bv);
      }
      return sortAsc ? cmp : -cmp;
    });

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) =>
    sortKey === col ? (
      sortAsc ? (
        <ChevronUp size={12} />
      ) : (
        <ChevronDown size={12} />
      )
    ) : null;

  const sevCounts = alerts.reduce<Record<string, number>>((acc, a) => {
    acc[a.severity] = (acc[a.severity] || 0) + 1;
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-amber/30 border-t-accent-amber rounded-full animate-spin" />
          <span className="text-sm text-text-muted">Loading alerts...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("h-full flex", newCritical && "critical-flash")}>
      <div className="flex-1 flex flex-col min-w-0 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold mb-1">Alerts</h1>
            <p className="text-sm text-text-muted">
              {alerts.length} total alerts across all sources
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* View mode toggle */}
            <div className="flex items-center gap-1 bg-bg-deep rounded-lg p-0.5 border border-white/5">
              <button
                onClick={() => setViewMode("table")}
                className={cn(
                  "px-2.5 py-1.5 rounded-md text-xs transition-all",
                  viewMode === "table"
                    ? "bg-accent-blue/20 text-accent-blue"
                    : "text-text-muted hover:text-text-secondary"
                )}
              >
                <List size={14} />
              </button>
              <button
                onClick={() => setViewMode("timeline")}
                className={cn(
                  "px-2.5 py-1.5 rounded-md text-xs transition-all",
                  viewMode === "timeline"
                    ? "bg-accent-blue/20 text-accent-blue"
                    : "text-text-muted hover:text-text-secondary"
                )}
              >
                <Clock size={14} />
              </button>
            </div>

            {/* Sound toggle */}
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={cn(
                "p-1.5 rounded-lg border transition-all",
                soundEnabled
                  ? "bg-accent-amber/10 border-accent-amber/30 text-accent-amber"
                  : "border-white/5 text-text-muted hover:text-text-secondary"
              )}
              title={soundEnabled ? "Sound alerts enabled" : "Sound alerts disabled"}
            >
              {soundEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
            </button>

            {/* Severity filter pills */}
            <div className="flex items-center gap-2">
              <Filter size={14} className="text-text-muted" />
              <button
                onClick={() => setFilterSev(null)}
                className={cn(
                  "px-2.5 py-1 rounded-lg text-xs transition-colors",
                  !filterSev
                    ? "bg-accent-blue/20 text-accent-blue"
                    : "text-text-muted hover:text-text-secondary"
                )}
              >
                All ({alerts.length})
              </button>
              {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => (
                <button
                  key={s}
                  onClick={() => setFilterSev(filterSev === s ? null : s)}
                  className={cn(
                    "px-2.5 py-1 rounded-lg text-xs border transition-colors",
                    filterSev === s
                      ? severityBg(s)
                      : "border-transparent text-text-muted hover:text-text-secondary"
                  )}
                >
                  {s} ({sevCounts[s] || 0})
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sparkline */}
        <div className="mb-4">
          <SeveritySparkline alerts={alerts} />
        </div>

        {/* Table or Timeline */}
        {viewMode === "table" ? (
          <div className="flex-1 overflow-y-auto rounded-xl border border-white/5">
            <table className="w-full">
              <thead className="sticky top-0 bg-bg-surface z-10">
                <tr className="border-b border-white/5">
                  {[
                    { key: "severity" as SortKey, label: "Severity", w: "w-28" },
                    { key: "title" as SortKey, label: "Title", w: "flex-1" },
                    { key: "alert_type" as SortKey, label: "Type", w: "w-40" },
                    { key: "created_at" as SortKey, label: "Date", w: "w-36" },
                  ].map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className={cn(
                        "text-left text-[10px] uppercase tracking-wider text-text-muted font-semibold px-4 py-3 cursor-pointer hover:text-text-secondary select-none",
                        col.w
                      )}
                    >
                      <span className="flex items-center gap-1">
                        {col.label} <SortIcon col={col.key} />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((a, i) => (
                  <tr
                    key={a.id || i}
                    onClick={() => setSelected(a)}
                    className={cn(
                      "border-b border-white/[0.03] cursor-pointer transition-colors",
                      selected?.id === a.id ? "bg-bg-hover" : "hover:bg-bg-hover/50",
                      a.severity === "CRITICAL" && "pulse-critical"
                    )}
                  >
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex px-2 py-0.5 rounded text-[10px] font-semibold border",
                          severityBg(a.severity)
                        )}
                      >
                        {a.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-text-primary truncate max-w-[400px]">
                      {a.title}
                    </td>
                    <td className="px-4 py-3 text-xs text-text-muted font-mono">
                      {a.alert_type || "general"}
                    </td>
                    <td className="px-4 py-3 text-xs text-text-muted font-mono">
                      {a.created_at ? new Date(a.created_at).toLocaleDateString() : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <TimelineView alerts={sorted} onSelect={setSelected} selected={selected} />
        )}
      </div>

      {/* Detail panel */}
      {selected && (
        <div className="w-96 border-l border-white/5 bg-bg-surface p-6 overflow-y-auto animate-slide-in-right">
          <div className="flex items-center justify-between mb-4">
            <span
              className={cn(
                "px-2.5 py-1 rounded text-xs font-semibold border",
                severityBg(selected.severity)
              )}
            >
              {selected.severity}
            </span>
            <button
              onClick={() => setSelected(null)}
              className="text-text-muted hover:text-text-primary"
            >
              <X size={16} />
            </button>
          </div>

          <h2 className="text-lg font-semibold mb-3">{selected.title}</h2>
          <p className="text-sm text-text-secondary leading-relaxed mb-4">
            {selected.description}
          </p>

          {selected.alert_type && (
            <div className="flex items-center gap-2 mb-2 text-xs">
              <span className="text-text-muted">Type:</span>
              <span className="font-mono text-text-secondary">{selected.alert_type}</span>
            </div>
          )}
          {selected.created_at && (
            <div className="flex items-center gap-2 mb-4 text-xs">
              <span className="text-text-muted">Created:</span>
              <span className="font-mono text-text-secondary">
                {new Date(selected.created_at).toLocaleString()}
              </span>
            </div>
          )}

          {selected.payload && Object.keys(selected.payload).length > 0 && (
            <>
              <div className="text-[10px] uppercase tracking-wider text-text-muted font-semibold mb-2 mt-4">
                Payload Data
              </div>
              <div className="bg-bg-deep rounded-lg p-3 space-y-1.5">
                {Object.entries(selected.payload).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-text-muted">{k}</span>
                    <span className="text-text-secondary font-mono truncate max-w-[180px]">
                      {typeof v === "object" ? JSON.stringify(v) : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
