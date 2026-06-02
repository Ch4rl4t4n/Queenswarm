"use client";

import Link from "next/link";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { useMissionSearch } from "@/lib/use-mission-search";

/** Hermes-style live search across supervisor sessions and kanban tasks. */
export function HiveSessionSearchPanel() {
  const { query, setQuery, result, busy, error } = useMissionSearch(300);

  return (
    <V4Card>
      <V4CardHeader
        kicker="Session memory"
        title="Hive mission search"
        description="Live search across supervisor goals, sub-agent summaries, and kanban tasks."
      />
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="e.g. landing page, sentinel, content week…"
        className="qs-input w-full text-sm"
      />
      {busy ? <p className="mt-2 text-xs text-pollen">Searching…</p> : null}
      {error ? <p className="mt-2 text-sm text-(--qs-red)">{error}</p> : null}

      {result.tasks.length ? (
        <ul className="mt-4 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Tasks</p>
          {result.tasks.map((hit) => (
            <li key={hit.task_id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm">
              <Link href={`/tasks?task=${hit.task_id}`} className="font-semibold text-cyan hover:underline">
                {hit.title}
              </Link>
              <p className="text-xs text-(--qs-muted)">{hit.status}</p>
            </li>
          ))}
        </ul>
      ) : null}

      {result.sessions.length ? (
        <ul className="mt-4 space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-zinc-500">Sessions</p>
          {result.sessions.map((hit) => (
            <li key={hit.session_id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm">
              <Link href={`/agents?session=${hit.session_id}`} className="font-mono text-xs text-cyan hover:underline">
                {hit.session_id.slice(0, 8)}…
              </Link>
              <p className="mt-1 font-semibold text-(--qs-text)">{hit.goal_excerpt}</p>
              <p className="line-clamp-3 font-mono text-xs text-(--qs-text-3)">{hit.snippet}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </V4Card>
  );
}
