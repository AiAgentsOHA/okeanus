"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, X, MapPin } from "lucide-react";
import { useStore } from "@/lib/store";
import { search, type SearchResult } from "@/lib/api";
import { entityColorHex } from "@/lib/utils";

export function SearchDialog() {
  const open = useStore((s) => s.searchOpen);
  const setOpen = useStore((s) => s.setSearchOpen);
  const setSelected = useStore((s) => s.setSelectedEntity);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery("");
      setResults([]);
    }
  }, [open]);

  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await search(query, 10);
        setResults(r);
      } catch {
        setResults([]);
      }
      setLoading(false);
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-2xl bg-bg-elevated border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
          <Search size={18} className="text-text-muted shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search entities, regions, species..."
            className="flex-1 bg-transparent text-text-primary text-sm outline-none placeholder:text-text-muted"
            onKeyDown={(e) => {
              if (e.key === "Escape") setOpen(false);
            }}
          />
          {loading && (
            <div className="w-4 h-4 border-2 border-accent-cyan/30 border-t-accent-cyan rounded-full animate-spin" />
          )}
          <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-secondary">
            <X size={16} />
          </button>
        </div>

        {/* Results */}
        <div className="max-h-[400px] overflow-y-auto">
          {results.length === 0 && query.length >= 2 && !loading && (
            <div className="px-4 py-8 text-center text-text-muted text-sm">No results found</div>
          )}
          {results.map((r, i) => (
            <button
              key={r.id || i}
              onClick={() => {
                setSelected(r as unknown as Record<string, unknown>);
                setOpen(false);
                if (r.latitude && r.longitude) router.push("/");
              }}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-bg-hover transition-colors text-left"
            >
              <div
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: entityColorHex(r.entity_type) }}
              />
              <div className="flex-1 min-w-0">
                <div className="text-sm text-text-primary truncate">{r.name}</div>
                <div className="text-xs text-text-muted truncate">{r.description}</div>
              </div>
              <span className="text-[10px] font-mono text-text-muted uppercase px-1.5 py-0.5 bg-bg-deep rounded">
                {r.entity_type}
              </span>
              {r.latitude && (
                <MapPin size={12} className="text-text-muted shrink-0" />
              )}
              <span className="text-[10px] font-mono text-text-muted">
                {(r.score * 100).toFixed(0)}%
              </span>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-white/5 flex items-center gap-4 text-[10px] text-text-muted">
          <span>
            <kbd className="bg-bg-deep px-1 py-0.5 rounded font-mono">Esc</kbd> close
          </span>
          <span>
            <kbd className="bg-bg-deep px-1 py-0.5 rounded font-mono">Enter</kbd> select
          </span>
        </div>
      </div>
    </div>
  );
}
