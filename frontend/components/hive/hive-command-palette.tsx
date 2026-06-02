"use client";

import Link from "next/link";
import { Loader2, Search, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { useMissionSearch } from "@/lib/use-mission-search";
import { cn } from "@/lib/utils";

interface HiveCommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

/** Hermes-style ⌘K mission search — sessions + kanban tasks. */
export function HiveCommandPalette({ open, onClose }: HiveCommandPaletteProps): JSX.Element | null {
  const inputRef = useRef<HTMLInputElement>(null);
  const { query, setQuery, result, busy, error } = useMissionSearch(220);

  useEffect(() => {
    if (!open) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.setTimeout(() => inputRef.current?.focus(), 0);
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const hasHits = result.total > 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-black/70 p-4 pt-[12vh] backdrop-blur-sm">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="Close search" onClick={onClose} />
      <div className="relative z-10 w-full max-w-2xl overflow-hidden rounded-2xl border border-[color:var(--qs-border)] bg-[#080812] shadow-2xl">
        <div className="flex items-center gap-2 border-b border-[color:var(--qs-border)] px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-data" aria-hidden />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search sessions, tasks, goals…"
            className="min-w-0 flex-1 bg-transparent text-sm text-[#fafafa] placeholder:text-zinc-500 focus:outline-none"
          />
          {busy ? <Loader2 className="h-4 w-4 animate-spin text-pollen" aria-hidden /> : null}
          <button type="button" onClick={onClose} className="rounded-lg p-1 text-zinc-500 hover:text-zinc-200">
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div className="max-h-[50vh] overflow-y-auto p-3 hive-scrollbar">
          {error ? <p className="px-2 py-3 text-sm text-danger">{error}</p> : null}
          {!error && query.trim().length < 2 ? (
            <p className="px-2 py-6 text-center text-sm text-zinc-500">Type at least 2 characters…</p>
          ) : null}
          {!error && query.trim().length >= 2 && !busy && !hasHits ? (
            <p className="px-2 py-6 text-center text-sm text-zinc-500">No matches.</p>
          ) : null}

          {result.tasks.length ? (
            <section className="mb-4">
              <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Tasks</p>
              <ul className="space-y-1">
                {result.tasks.map((hit) => (
                  <li key={hit.task_id}>
                    <Link
                      href={`/tasks?task=${encodeURIComponent(hit.task_id)}`}
                      onClick={onClose}
                      className="block rounded-lg px-3 py-2 transition hover:bg-white/5"
                    >
                      <p className="text-sm font-medium text-[#fafafa]">{hit.title}</p>
                      <p className="text-[11px] uppercase text-zinc-500">
                        {hit.status}
                        {hit.match_source.includes("semantic") ? (
                          <span className="ml-2 normal-case text-data">· vector match</span>
                        ) : null}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {result.sessions.length ? (
            <section>
              <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Sessions</p>
              <ul className="space-y-1">
                {result.sessions.map((hit) => (
                  <li key={hit.session_id}>
                    <Link
                      href={`/agents?session=${encodeURIComponent(hit.session_id)}`}
                      onClick={onClose}
                      className="block rounded-lg px-3 py-2 transition hover:bg-white/5"
                    >
                      <p className="text-sm font-medium text-[#fafafa]">{hit.goal_excerpt}</p>
                      <p className="line-clamp-2 font-mono text-[11px] text-zinc-500">
                        {hit.snippet}
                        {hit.match_source.includes("semantic") ? (
                          <span className="ml-1 text-data">· vector</span>
                        ) : null}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        <div className="border-t border-[color:var(--qs-border)] px-4 py-2 text-[11px] text-zinc-600">
          <span className={cn("rounded border border-white/10 px-1.5 py-0.5 font-mono")}>Esc</span> close ·{" "}
          <span className="rounded border border-white/10 px-1.5 py-0.5 font-mono">⌘K</span> toggle
        </div>
      </div>
    </div>
  );
}

export function useHiveCommandPaletteShortcut(onOpen: () => void): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpen();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onOpen]);
}
