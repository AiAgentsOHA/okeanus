import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

export function severityColor(severity: string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "text-accent-red";
    case "HIGH":
      return "text-accent-amber";
    case "MEDIUM":
      return "text-accent-blue";
    case "LOW":
      return "text-text-muted";
    default:
      return "text-text-secondary";
  }
}

export function severityBg(severity: string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "bg-accent-red/20 border-accent-red/40 text-accent-red";
    case "HIGH":
      return "bg-accent-amber/20 border-accent-amber/40 text-accent-amber";
    case "MEDIUM":
      return "bg-accent-blue/20 border-accent-blue/40 text-accent-blue";
    case "LOW":
      return "bg-bg-hover border-text-muted/30 text-text-muted";
    default:
      return "bg-bg-hover border-text-muted/30 text-text-secondary";
  }
}

export function entityColor(type: string): [number, number, number, number] {
  switch (type?.toLowerCase()) {
    case "species":
      return [6, 182, 212, 200];
    case "infrastructure":
      return [245, 158, 11, 200];
    case "region":
      return [16, 185, 129, 200];
    case "event":
      return [239, 68, 68, 200];
    case "assessment":
      return [139, 92, 246, 200];
    case "flow":
      return [59, 130, 246, 200];
    default:
      return [148, 163, 184, 200];
  }
}

export function entityColorHex(type: string): string {
  switch (type?.toLowerCase()) {
    case "species":
      return "#06B6D4";
    case "infrastructure":
      return "#F59E0B";
    case "region":
      return "#10B981";
    case "event":
      return "#EF4444";
    case "assessment":
      return "#8B5CF6";
    case "flow":
      return "#3B82F6";
    default:
      return "#94A3B8";
  }
}
