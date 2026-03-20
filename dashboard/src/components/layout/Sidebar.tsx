"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Globe2,
  Network,
  BarChart3,
  AlertTriangle,
  Search,
  GitBranch,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", icon: Globe2, label: "Globe", desc: "Global intelligence map" },
  { href: "/graph", icon: Network, label: "Graph", desc: "Entity relationship graph" },
  { href: "/analytics", icon: BarChart3, label: "Analytics", desc: "Data analysis & trends" },
  { href: "/alerts", icon: AlertTriangle, label: "Alerts", desc: "Threat notifications" },
  { href: "/investigate", icon: Search, label: "Investigate", desc: "AI-powered investigation" },
  { href: "/lineage", icon: GitBranch, label: "Lineage", desc: "Data source tracking" },
];

export function Sidebar() {
  const pathname = usePathname();
  const [criticalCount, setCriticalCount] = useState(0);

  // Fetch critical alert count for notification badge
  useEffect(() => {
    fetch("/api/alerts?limit=500")
      .then((r) => r.json())
      .then((d: Array<{ severity?: string }>) => {
        if (Array.isArray(d)) {
          const count = d.filter(
            (a) => a.severity?.toUpperCase() === "CRITICAL"
          ).length;
          setCriticalCount(count);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <nav className="w-[72px] h-full bg-bg-surface border-r border-white/5 flex flex-col items-center py-4 gap-1 shrink-0">
      {/* Brand — Okeanus Logo */}
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-blue flex items-center justify-center mb-6 shadow-lg shadow-accent-cyan/20 animate-glow-pulse">
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="white"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M2 12c2.5-3 5.5-5 10-5s7.5 2 10 5" />
          <path d="M2 12c2.5 3 5.5 5 10 5s7.5-2 10-5" />
          <line x1="12" y1="2" x2="12" y2="22" />
        </svg>
      </div>

      {/* Nav items */}
      {navItems.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        const isAlerts = item.href === "/alerts";
        return (
          <div key={item.href} className="tooltip-wrapper relative">
            <Link
              href={item.href}
              className={cn(
                "w-14 h-14 rounded-xl flex flex-col items-center justify-center gap-1 transition-all duration-200 relative",
                active
                  ? "bg-accent-blue/15 text-accent-blue nav-active-glow"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-hover hover:scale-105"
              )}
            >
              <item.icon size={20} strokeWidth={active ? 2.2 : 1.5} />
              <span className="text-[10px] font-medium">{item.label}</span>
              {/* Notification badge on Alerts */}
              {isAlerts && criticalCount > 0 && (
                <span className="notification-badge">
                  {criticalCount > 99 ? "99+" : criticalCount}
                </span>
              )}
            </Link>
            {/* Tooltip */}
            <span className="tooltip-text">{item.desc}</span>
          </div>
        );
      })}

      {/* Version at bottom */}
      <div className="mt-auto">
        <span className="text-[9px] text-text-muted font-mono opacity-60">v1.0</span>
      </div>
    </nav>
  );
}
