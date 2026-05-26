"use client";

import Link from "next/link";
import { Loader2, Search } from "lucide-react";
import { useCallback, useState } from "react";

import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";

interface SessionHit {
  session_id: string;
  status: string;
  goal_excerpt: string;
  created_at: string | null;
  hivemind_verify_status?: string;
  match_source: string;
  snippet: string;
}

/** Hermes Tier-2 style search across supervisor sessions. */
export function HiveSessionSearchPanel() {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SessionHit[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const search = useCallback(async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setBusy(true);
    try {
      const body = await hiveGet<{ hits: SessionHit[] }>(
        `solo-operator/session-search?q=${encodeURIComponent(q)}&limit=15`,
      );
      setHits(body.hits);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Search failed");
      setHits([]);
    } finally {
      setBusy(false);
    }
  }, [query]);

  return (
    <V4Card>
      <V4CardHeader
        kicker="Session memory"
        title="Hive session search"
        description="Full-text search across supervisor goals and sub-agent summaries — swarm-wide, not single chat."
      />
      <div className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void search();
          }}
          placeholder="e.g. sentinel, maintainer, stalled project…"
          className="qs-input flex-1 text-sm"
        />
        <button type="button" className="qs-btn qs-btn--primary qs-btn--sm" disabled={busy} onClick={() => void search()}>
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" aria-hidden />}
          Search
        </button>
      </div>
      {err ? <p className="mt-2 text-sm text-(--qs-red)">{err}</p> : null}
      <ul className="mt-4 space-y-2">
        {hits.map((hit) => (
          <li key={hit.session_id} className="rounded-lg border border-(--qs-border) bg-black/20 px-3 py-2 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link href={`/agents?session=${hit.session_id}`} className="font-mono text-xs text-cyan hover:underline">
                {hit.session_id.slice(0, 8)}…
              </Link>
              <span className="font-mono text-xs text-(--qs-muted)">{hit.status}</span>
            </div>
            <p className="mt-1 font-semibold text-(--qs-text)">{hit.goal_excerpt}</p>
            <p className="mt-1 text-xs text-(--qs-muted)">{hit.match_source}</p>
            <p className="mt-1 line-clamp-3 font-mono text-xs text-(--qs-text-3)">{hit.snippet}</p>
          </li>
        ))}
      </ul>
    </V4Card>
  );
}
