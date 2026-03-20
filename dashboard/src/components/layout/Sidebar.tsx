"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
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
  { href: "/", icon: Globe2, label: "Globe" },
  { href: "/graph", icon: Network, label: "Graph" },
  { href: "/analytics", icon: BarChart3, label: "Analytics" },
  { href: "/alerts", icon: AlertTriangle, label: "Alerts" },
  { href: "/investigate", icon: Search, label: "Investigate" },
  { href: "/lineage", icon: GitBranch, label: "Lineage" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="w-[72px] h-full bg-bg-surface border-r border-white/5 flex flex-col items-center py-4 gap-1 shrink-0">
      {/* Brand */}
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-cyan to-accent-blue flex items-center justify-center mb-6">
        <span className="text-white font-bold text-lg">O</span>
      </div>

      {/* Nav items */}
      {navItems.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "w-14 h-14 rounded-xl flex flex-col items-center justify-center gap-1 transition-all duration-200",
              active
                ? "bg-accent-blue/15 text-accent-blue"
                : "text-text-muted hover:text-text-secondary hover:bg-bg-hover"
            )}
          >
            <item.icon size={20} strokeWidth={active ? 2.2 : 1.5} />
            <span className="text-[10px] font-medium">{item.label}</span>
          </Link>
        );
      })}

      {/* Version at bottom */}
      <div className="mt-auto">
        <span className="text-[9px] text-text-muted font-mono">v1.0</span>
      </div>
    </nav>
  );
}
