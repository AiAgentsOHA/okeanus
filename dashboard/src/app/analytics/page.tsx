"use client";

import { useEffect, useState } from "react";
import { BarChart3, TrendingUp, Activity, AlertTriangle, Calendar, Award } from "lucide-react";
import { entityColorHex, cn } from "@/lib/utils";

interface ChartData {
  entityDist: { entity_type: string; count: number }[];
  temporal: { period: string; count: number }[];
  sources: { source: string; count: number }[];
  severity: { severity: string; count: number }[];
  eventFreq: { date: string; count: number }[];
  rankings: { name: string; score: number; entity_type: string }[];
}

export default function AnalyticsPage() {
  const [data, setData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/analytics/entities/distribution").then((r) => r.json()).catch(() => []),
      fetch("/api/analytics/observations/temporal").then((r) => r.json()).catch(() => []),
      fetch("/api/analytics/observations/sources").then((r) => r.json()).catch(() => []),
      fetch("/api/analytics/events/severity-trend").then((r) => r.json()).catch(() => []),
      fetch("/api/analytics/events/frequency").then((r) => r.json()).catch(() => []),
      fetch("/api/analytics/assessments/ranking").then((r) => r.json()).catch(() => []),
    ]).then(([entityDist, temporal, sources, severity, eventFreq, rankings]) => {
      setData({ entityDist, temporal, sources, severity, eventFreq, rankings });
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
          <span className="text-sm text-text-muted">Loading analytics...</span>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const totalEntities = data.entityDist.reduce((s, d) => s + d.count, 0);
  const totalObs = data.temporal.reduce((s, d) => s + d.count, 0);
  const maxSource = data.sources.reduce((m, d) => (d.count > m.count ? d : m), { source: "", count: 0 });

  return (
    <div className="h-full overflow-y-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Analytics Dashboard</h1>
        <p className="text-sm text-text-muted">Ocean intelligence metrics and trends</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={BarChart3} label="Total Entities" value={totalEntities.toLocaleString()} color="text-accent-cyan" />
        <KPICard icon={Activity} label="Observations" value={totalObs.toLocaleString()} color="text-accent-emerald" />
        <KPICard icon={AlertTriangle} label="Alert Types" value={data.severity.length.toString()} color="text-accent-amber" />
        <KPICard icon={Award} label="Top Source" value={maxSource.source || "N/A"} color="text-accent-violet" sub={`${maxSource.count.toLocaleString()} records`} />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Entity Distribution */}
        <ChartCard title="Entity Type Distribution" icon={BarChart3}>
          <div className="space-y-2">
            {data.entityDist.map((d) => {
              const pct = totalEntities > 0 ? (d.count / totalEntities) * 100 : 0;
              return (
                <div key={d.entity_type} className="flex items-center gap-3">
                  <div className="w-20 text-xs text-text-secondary capitalize truncate">
                    {d.entity_type}
                  </div>
                  <div className="flex-1 h-5 bg-bg-deep rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: entityColorHex(d.entity_type),
                        opacity: 0.8,
                      }}
                    />
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-text-muted">
                    {d.count.toLocaleString()}
                  </div>
                  <div className="w-12 text-right font-mono text-[10px] text-text-muted">
                    {pct.toFixed(1)}%
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>

        {/* Source Breakdown */}
        <ChartCard title="Source Breakdown" icon={Activity}>
          <div className="space-y-2">
            {data.sources.slice(0, 10).map((d, i) => {
              const maxCount = data.sources[0]?.count || 1;
              const pct = (d.count / maxCount) * 100;
              return (
                <div key={d.source || i} className="flex items-center gap-3">
                  <div className="w-28 text-xs text-text-secondary truncate">
                    {d.source}
                  </div>
                  <div className="flex-1 h-4 bg-bg-deep rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-accent-blue/70 transition-all duration-700"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-text-muted">
                    {d.count.toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Temporal Coverage */}
        <ChartCard title="Temporal Observation Coverage" icon={TrendingUp}>
          <div className="flex items-end gap-px h-40">
            {data.temporal.slice(-60).map((d, i) => {
              const maxC = Math.max(...data.temporal.map((t) => t.count), 1);
              const h = (d.count / maxC) * 100;
              return (
                <div
                  key={i}
                  className="flex-1 bg-accent-cyan/60 rounded-t hover:bg-accent-cyan/80 transition-colors group relative"
                  style={{ height: `${Math.max(h, 2)}%` }}
                >
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block glass rounded px-1.5 py-0.5 text-[9px] font-mono text-text-primary whitespace-nowrap z-10">
                    {d.period}: {d.count}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-1 text-[9px] text-text-muted font-mono">
            <span>{data.temporal[0]?.period || ""}</span>
            <span>{data.temporal[data.temporal.length - 1]?.period || ""}</span>
          </div>
        </ChartCard>

        {/* Severity Distribution */}
        <ChartCard title="Alert Severity Distribution" icon={AlertTriangle}>
          <div className="grid grid-cols-2 gap-4">
            {data.severity.map((d) => {
              const colors: Record<string, string> = {
                CRITICAL: "#EF4444",
                HIGH: "#F59E0B",
                MEDIUM: "#3B82F6",
                LOW: "#64748B",
              };
              return (
                <div key={d.severity} className="text-center">
                  <div
                    className="text-3xl font-bold font-mono mb-1"
                    style={{ color: colors[d.severity] || "#94A3B8" }}
                  >
                    {d.count}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-text-muted">
                    {d.severity}
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Event Frequency */}
        <ChartCard title="Event Frequency" icon={Calendar}>
          <div className="flex items-end gap-px h-32">
            {data.eventFreq.slice(-40).map((d, i) => {
              const maxC = Math.max(...data.eventFreq.map((t) => t.count), 1);
              const h = (d.count / maxC) * 100;
              return (
                <div
                  key={i}
                  className="flex-1 bg-accent-amber/50 rounded-t hover:bg-accent-amber/70 transition-colors group relative"
                  style={{ height: `${Math.max(h, 2)}%` }}
                >
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block glass rounded px-1.5 py-0.5 text-[9px] font-mono text-text-primary whitespace-nowrap z-10">
                    {d.date}: {d.count}
                  </div>
                </div>
              );
            })}
          </div>
        </ChartCard>

        {/* Top Assessments */}
        <ChartCard title="Assessment Rankings" icon={Award}>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {data.rankings.slice(0, 10).map((d, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="w-5 text-center font-mono text-xs text-text-muted">
                  {i + 1}
                </span>
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: entityColorHex(d.entity_type) }}
                />
                <span className="flex-1 text-xs text-text-secondary truncate">
                  {d.name}
                </span>
                <span className="font-mono text-xs text-accent-cyan">
                  {typeof d.score === "number" ? d.score.toFixed(2) : d.score}
                </span>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

function KPICard({
  icon: Icon,
  label,
  value,
  color,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color: string;
  sub?: string;
}) {
  return (
    <div className="bg-bg-surface border border-white/5 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon size={14} className={color} />
        <span className="text-[10px] uppercase tracking-wider text-text-muted font-semibold">
          {label}
        </span>
      </div>
      <div className="text-xl font-bold font-mono">{value}</div>
      {sub && <div className="text-[10px] text-text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

function ChartCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-bg-surface border border-white/5 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Icon size={14} className="text-text-muted" />
        <span className="text-xs font-semibold text-text-secondary">{title}</span>
      </div>
      {children}
    </div>
  );
}
