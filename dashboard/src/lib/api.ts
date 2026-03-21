const BASE = "/api";

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 30 } });
  if (!res.ok) throw new Error(`API ${path}: ${res.status}`);
  return res.json();
}

// Health
export const getHealth = () => fetchJSON<{ status: string }>("/health");

// Alerts
export interface Alert {
  id?: string;
  severity: string;
  title: string;
  description: string;
  alert_type?: string;
  created_at?: string;
  payload?: Record<string, unknown>;
}
export const getAlerts = (limit = 50) =>
  fetchJSON<Alert[]>(`/alerts?limit=${limit}`);

// Lineage
export interface SourceCoverage {
  source_name: string;
  adapter_type: string;
  observation_count: number;
  entity_count: number;
  last_run?: string;
}
export const getLineageSources = () =>
  fetchJSON<SourceCoverage[]>("/lineage/sources");

// Analytics - Spatial
export const getHotspots = () => fetchJSON<unknown[]>("/analytics/hotspots");
export const getDensity = () => fetchJSON<unknown[]>("/analytics/entities/density");
export const getSpatialClusters = () =>
  fetchJSON<unknown[]>("/analytics/spatial-clusters");
export const getTrajectories = () =>
  fetchJSON<unknown[]>("/analytics/trajectories");
export const getEncounters = () =>
  fetchJSON<unknown[]>("/analytics/encounters");
export const getAutocorrelation = () =>
  fetchJSON<unknown>("/analytics/autocorrelation");

// Analytics - Time Series
export const getTimeseriesTrend = (code: string) =>
  fetchJSON<unknown>(`/analytics/timeseries/trend?code=${code}`);
export const getVolatility = () =>
  fetchJSON<unknown>("/analytics/timeseries/volatility");

// Analytics - Entities
export const getEntityDistribution = () =>
  fetchJSON<unknown[]>("/analytics/entities/distribution");
export const getEntityDensity = () =>
  fetchJSON<unknown[]>("/analytics/entities/density");

// Analytics - Observations
export const getObservationSources = () =>
  fetchJSON<unknown[]>("/analytics/observations/sources");
export const getObservationTemporal = () =>
  fetchJSON<unknown[]>("/analytics/observations/temporal");

// Analytics - Events
export const getEventFrequency = () =>
  fetchJSON<unknown[]>("/analytics/events/frequency");
export const getSeverityTrend = () =>
  fetchJSON<unknown[]>("/analytics/events/severity-trend");

// Analytics - Assessments
export const getAssessmentRanking = () =>
  fetchJSON<unknown[]>("/analytics/assessments/ranking");

// Analytics - Network
export const getFlowNetwork = () =>
  fetchJSON<{ nodes: unknown[]; edges: unknown[] }>("/analytics/flows/network");
export const getRelationshipCentrality = () =>
  fetchJSON<unknown[]>("/analytics/relationships/centrality");
export const getRelationshipComponents = () =>
  fetchJSON<unknown[]>("/analytics/relationships/components");

// Decision Tree / Lineage
export interface DecisionTree {
  entity_id: string;
  entity?: {
    id: string;
    name: string;
    entity_type: string;
    source_name: string;
    sector?: string;
    country?: string;
    lat?: number;
    lon?: number;
  };
  layers: {
    name: string;
    label: string;
    nodes?: unknown[];
    edges?: unknown[];
    count?: number;
    community?: {
      community_id: number;
      size: number;
      pagerank?: number;
      centrality?: number;
    } | null;
    insights?: {
      id: string;
      insight_type: string;
      title: string;
      description: string;
      confidence: number;
      generator: string;
      status: string;
      created_at?: string;
      reasoning_traces: {
        id: string;
        phase: string;
        input_text: string;
        output_text: string;
      }[];
    }[];
  }[];
  error?: string;
}
export const getDecisionTree = (entityId: string) =>
  fetchJSON<DecisionTree>(`/lineage/tree/${entityId}`);

// Search
export interface SearchResult {
  id: string;
  entity_type: string;
  name: string;
  description?: string;
  score: number;
  latitude?: number;
  longitude?: number;
}
export const search = (query: string, limit = 10) =>
  fetch(`${BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  }).then((r) => r.json() as Promise<SearchResult[]>);

// Investigation (SSE)
export function investigate(
  query: string,
  onChunk: (text: string) => void,
  onDone: () => void
) {
  const controller = new AbortController();
  fetch(`${BASE}/ml/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
    signal: controller.signal,
  })
    .then(async (res) => {
      const reader = res.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.token) onChunk(data.token);
              else if (data.text) onChunk(data.text);
              else if (typeof data === "string") onChunk(data);
            } catch {
              onChunk(line.slice(6));
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") console.error(err);
      onDone();
    });
  return controller;
}
