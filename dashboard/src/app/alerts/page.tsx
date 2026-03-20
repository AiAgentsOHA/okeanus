"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, X, Filter } from "lucide-react";
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

const SEV_ORDER: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("severity");
  const [sortAsc, setSortAsc] = useState(true);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [filterSev, setFilterSev] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/alerts?limit=200")
      .then((r) => r.json())
      .then((d) => {
        if (Array.isArray(d)) setAlerts(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

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
      sortAsc ? <ChevronUp size={12} /> : <ChevronDown size={12} />
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
    <div className="h-full flex">
      {/* Main table area */}
      <div className="flex-1 flex flex-col min-w-0 p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold mb-1">Alerts</h1>
            <p className="text-sm text-text-muted">{alerts.length} total alerts across all sources</p>
          </div>
          {/* Severity filter pills */}
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-text-muted" />
            <button
              onClick={() => setFilterSev(null)}
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs transition-colors",
                !filterSev ? "bg-accent-blue/20 text-accent-blue" : "text-text-muted hover:text-text-secondary"
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
                  filterSev === s ? severityBg(s) : "border-transparent text-text-muted hover:text-text-secondary"
                )}
              >
                {s} ({sevCounts[s] || 0})
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
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
                    selected?.id === a.id
                      ? "bg-bg-hover"
                      : "hover:bg-bg-hover/50",
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

          {/* Payload */}
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
