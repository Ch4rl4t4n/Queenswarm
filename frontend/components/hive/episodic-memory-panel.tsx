"use client";

import Link from "next/link";
import { Clock3, Loader2Icon } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  DynamicCollectorDeck,
  type CollectorCardItem,
  type CollectorTab,
} from "@/components/hive/dynamic-collector-deck";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { sectionHintNode } from "@/components/hive/inline-section-hint";
import { V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import type { EpisodicMemoryItemRow, EpisodicMemoryPayload, EpisodicSummaryPayload } from "@/lib/hive-types";
function kindTone(kind: string): "ok" | "warn" | "info" | "err" {
  if (kind === "dump_sleep") return "ok";
  if (kind === "dream_insight") return "info";
  if (kind === "episodic_capture") return "ok";
  if (kind === "session_summary") return "warn";
  return "info";
}

function kindLabel(kind: string): string {
  return kind.replaceAll("_", " ");
}

function filterKind(item: EpisodicMemoryItemRow, tabId: string): boolean {
  if (tabId === "all") return true;
  if (tabId === "events") {
    return item.kind === "session_event" || item.kind === "session_summary" || item.kind === "episodic_capture";
  }
  if (tabId === "insights") return item.kind === "dream_insight";
  if (tabId === "dump") return item.kind === "dump_sleep";
  return true;
}

function toCard(item: EpisodicMemoryItemRow): CollectorCardItem {
  const when = new Date(item.occurred_at).toLocaleString("sk-SK");
  return {
    id: item.id,
    title: item.title,
    body: item.summary,
    meta: when,
    badge: kindLabel(item.kind),
    badgeTone: kindTone(item.kind),
    footer: item.session_id ? (
      <Link
        href={`/agents?session=${encodeURIComponent(item.session_id)}`}
        className="qs-btn qs-btn--ghost qs-btn--sm"
      >
        Open session {item.session_id.slice(0, 8)}…
      </Link>
    ) : undefined,
  };
}

/** Episodic memory — dynamic collector tabs + card deck (Pattern 8). */
export function EpisodicMemoryPanel(): JSX.Element {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [summary, setSummary] = useState<EpisodicSummaryPayload | null>(null);
  const [timeline, setTimeline] = useState<EpisodicMemoryPayload | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([
        hiveGet<EpisodicSummaryPayload>("memory/episodic/summary"),
        hiveGet<EpisodicMemoryPayload>("memory/episodic/timeline?limit=100"),
      ]);
      setSummary(s);
      setTimeline(t);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Episodic memory unavailable.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const items = useMemo(() => timeline?.items ?? [], [timeline?.items]);

  const tabs: CollectorTab[] = useMemo(
    () => [
      { id: "all", label: "All", count: items.length, tone: "info" },
      {
        id: "events",
        label: "Events",
        count: summary?.counts.session_events ?? items.filter((i) => filterKind(i, "events")).length,
        tone: "info",
      },
      {
        id: "insights",
        label: "Insights",
        count: summary?.counts.dream_insights ?? items.filter((i) => filterKind(i, "insights")).length,
        tone: "purple",
      },
      {
        id: "dump",
        label: "Dump",
        count: summary?.counts.dump_sleep_batches ?? items.filter((i) => filterKind(i, "dump")).length,
        tone: "ok",
      },
    ],
    [items, summary],
  );

  const itemsByTab = useMemo(() => {
    const map: Record<string, CollectorCardItem[]> = {};
    for (const tab of tabs) {
      map[tab.id] = items.filter((row) => filterKind(row, tab.id)).map(toCard);
    }
    return map;
  }, [items, tabs]);

  return (
    <V4Card className="mt-6 border-cyan/20">
      <V4CardHeader
        kicker="Episodic memory"
        title="Session timeline"
        description="Supervisor events, dream insights, and overnight ingest — flip through the collector deck."
        hint={sectionHintNode("knowledgeEpisodicMemory")}
        actions={
          <div className="flex items-center gap-2">
            <HiveRefreshButton
              busy={refreshing}
              onClick={() => {
                setRefreshing(true);
                void load();
              }}
            />
            <Link href="/agents#sessions" className="text-xs text-cyan underline-offset-2 hover:underline">
              Sessions
            </Link>
          </div>
        }
      />

      {loading ? (
        <p className="flex items-center gap-2 text-sm text-(--qs-text-3)">
          <Loader2Icon className="h-4 w-4 animate-spin" aria-hidden /> Loading episodic feed…
        </p>
      ) : null}

      {err ? <p className="text-sm text-(--qs-red)">{err}</p> : null}

      {!loading && !err && summary ? (
        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
          <Clock3 className="h-4 w-4 text-cyan" aria-hidden />
          <span className="text-(--qs-text-2)">
            {summary.retention_days}d retention · {summary.total_items} items
          </span>
        </div>
      ) : null}

      {!loading && !err ? (
        <DynamicCollectorDeck
          tabs={tabs}
          itemsByTab={itemsByTab}
          defaultTabId="events"
          emptyLabel="No episodic items in this collector — run supervisor sessions or dreaming."
        />
      ) : null}
    </V4Card>
  );
}
