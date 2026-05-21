"use client";

import Link from "next/link";
import { Clock3, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { EpisodicMemoryPayload, EpisodicSummaryPayload } from "@/lib/hive-types";

function kindTone(kind: string): "ok" | "warn" | "info" | "err" {
  if (kind === "dump_sleep") return "ok";
  if (kind === "dream_insight") return "info";
  if (kind === "session_summary") return "warn";
  return "info";
}

/** Episodic memory timeline — session events, dream insights, overnight ingest (Pattern 8). */
export function EpisodicMemoryPanel(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [summary, setSummary] = useState<EpisodicSummaryPayload | null>(null);
  const [timeline, setTimeline] = useState<EpisodicMemoryPayload | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([
        hiveGet<EpisodicSummaryPayload>("memory/episodic/summary"),
        hiveGet<EpisodicMemoryPayload>("memory/episodic/timeline?limit=24"),
      ]);
      setSummary(s);
      setTimeline(t);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Episodic memory unavailable.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <V4Card className="mt-6 border-cyan/20">
      <V4CardHeader
        kicker="Episodic memory"
        title="Session timeline"
        description="Supervisor events, dream insights, and overnight ingest — 30–90 day rolling window."
        actions={
          <Link href="/agents#sessions" className="text-xs text-cyan underline-offset-2 hover:underline">
            Sessions
          </Link>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading episodic feed…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && summary ? (
        <div className="mb-4 flex flex-wrap gap-2 text-xs">
          <Clock3 className="h-4 w-4 text-cyan" aria-hidden />
          <span className="text-(--qs-text-2)">{summary.retention_days}d retention · {summary.total_items} items</span>
          <V4Badge tone="info">events {summary.counts.session_events}</V4Badge>
          <V4Badge tone="info">insights {summary.counts.dream_insights}</V4Badge>
          <V4Badge tone="ok">dump {summary.counts.dump_sleep_batches}</V4Badge>
        </div>
      ) : null}

      {!loading && !err && timeline ? (
        <ul className="space-y-3">
          {timeline.items.map((item) => (
            <li key={item.id} className="rounded-xl border border-(--qs-border) bg-black/25 p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <V4Badge tone={kindTone(item.kind)}>{item.kind.replaceAll("_", " ")}</V4Badge>
                <span className="text-[11px] text-(--qs-text-3)">
                  {new Date(item.occurred_at).toLocaleString("sk-SK")}
                </span>
              </div>
              <p className="mt-2 font-medium text-(--qs-text-1)">{item.title}</p>
              <p className="mt-1 text-(--qs-text-2)">{item.summary}</p>
            </li>
          ))}
          {!timeline.items.length ? (
            <li className="text-sm text-(--qs-text-3)">No episodic items yet — run supervisor sessions or dreaming.</li>
          ) : null}
        </ul>
      ) : null}
    </V4Card>
  );
}
