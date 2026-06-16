"use client";

import { BookOpen, Clock3, Loader2, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { hiveGet } from "@/lib/api";

type TimelineEntryKind = "paper_fill" | "live_run" | "manual_entry" | "review_session";

interface JournalTimelineEntry {
  id: string;
  kind: TimelineEntryKind;
  title: string;
  detail: string;
  occurred_at: string;
  venue: string | null;
  symbol: string | null;
  side: string | null;
  notional_usd: number | null;
  pnl_usd: number | null;
  tags: string[];
  href: string | null;
}

interface JournalTimeline {
  enabled: boolean;
  generated_at: string;
  window_days: number;
  entry_count: number;
  paper_fill_count: number;
  live_run_count: number;
  manual_entry_count: number;
  review_session_count: number;
  items: JournalTimelineEntry[];
  operator_hint: string;
}

interface JournalStudioSnapshot {
  enabled: boolean;
  generated_at: string;
  enabled_field_count: number;
  mistake_tag_count: number;
  obsidian_subfolder: string;
  operator_hint: string;
  timeline_preview: JournalTimelineEntry[];
  routine: {
    routine_status: string;
    routine_name: string;
    next_run_at: string | null;
    operator_hint: string;
  } | null;
}

function kindBadge(kind: TimelineEntryKind): { label: string; tone: "ok" | "warn" | "info" | "purple" } {
  if (kind === "paper_fill") return { label: "Paper fill", tone: "info" };
  if (kind === "live_run") return { label: "Live run", tone: "ok" };
  if (kind === "manual_entry") return { label: "Manual", tone: "purple" };
  return { label: "Review", tone: "warn" };
}

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function JournalStudioTimelinePanel(): JSX.Element | null {
  const [timeline, setTimeline] = useState<JournalTimeline | null>(null);
  const [snapshot, setSnapshot] = useState<JournalStudioSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [timelineData, snapshotData] = await Promise.all([
        hiveGet<JournalTimeline>("journal-studio/timeline?limit=50&window_days=90"),
        hiveGet<JournalStudioSnapshot>("journal-studio/snapshot"),
      ]);
      setTimeline(timelineData);
      setSnapshot(snapshotData);
    } catch {
      setTimeline(null);
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return (
      <div data-testid="journal-studio-timeline-panel">
        <V4Card className="flex items-center gap-2 p-4 text-sm text-white/60">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading journal timeline…
        </V4Card>
      </div>
    );
  }

  if (!timeline?.enabled) {
    return (
      <div data-testid="journal-studio-timeline-panel">
        <V4Card className="p-4 text-sm text-white/60">
          Journal studio is disabled in deployment config.
        </V4Card>
      </div>
    );
  }

  const hint = snapshot?.operator_hint || timeline.operator_hint;

  return (
    <div className="space-y-4" data-testid="journal-studio-timeline-panel">
      <V4Card id="journal-studio-timeline" className="border-cyan-500/25">
        <V4CardHeader
          leadingIcon={BookOpen}
          title="Journal timeline"
          description="Paper fills, live runs, manual entries, and review sessions — newest first."
          actions={<HiveRefreshButton onClick={() => void load()} aria-label="Refresh journal timeline" />}
        />

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs uppercase tracking-wide text-white/50">Paper fills</p>
            <p className="font-mono text-lg text-cyan-300">{timeline.paper_fill_count}</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs uppercase tracking-wide text-white/50">Live runs</p>
            <p className="font-mono text-lg text-emerald-300">{timeline.live_run_count}</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs uppercase tracking-wide text-white/50">Manual entries</p>
            <p className="font-mono text-lg text-amber-300">{timeline.manual_entry_count}</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
            <p className="text-xs uppercase tracking-wide text-white/50">Review sessions</p>
            <p className="font-mono text-lg text-fuchsia-300">{timeline.review_session_count}</p>
          </div>
        </div>

        {snapshot ? (
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-white/60">
            <V4Badge tone="info">{snapshot.enabled_field_count} fields enabled</V4Badge>
            <V4Badge tone="purple">{snapshot.mistake_tag_count} mistake tags</V4Badge>
            <span>Obsidian: {snapshot.obsidian_subfolder}</span>
            {snapshot.routine ? (
              <V4Badge tone={snapshot.routine.routine_status === "scheduled" ? "ok" : "warn"}>
                {snapshot.routine.routine_status}
              </V4Badge>
            ) : null}
          </div>
        ) : null}

        <p className="mt-3 text-sm text-white/70">{hint}</p>
      </V4Card>

      <V4Card>
        <V4CardHeader
          leadingIcon={Clock3}
          title="Recent activity"
          description={`Last ${timeline.window_days} days · ${timeline.entry_count} entries`}
        />

        {timeline.items.length === 0 ? (
          <p className="mt-4 text-sm text-white/60">
            Timeline empty — paper fills, live runs, and review sessions appear here.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {timeline.items.map((entry) => {
              const badge = kindBadge(entry.kind);
              const row = (
                <div className="flex flex-col gap-1 rounded-lg border border-white/10 bg-white/[0.02] p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <V4Badge tone={badge.tone}>{badge.label}</V4Badge>
                    <span className="font-medium text-white">{entry.title}</span>
                    {entry.symbol ? (
                      <V4Badge tone="info">{entry.symbol}</V4Badge>
                    ) : null}
                    <span className="ml-auto text-xs text-white/50">{formatWhen(entry.occurred_at)}</span>
                  </div>
                  {entry.detail ? <p className="text-sm text-white/70">{entry.detail}</p> : null}
                  {entry.tags.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {entry.tags.map((tag) => (
                        <V4Badge key={`${entry.id}-${tag}`} tone="purple">
                          {tag}
                        </V4Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
              );

              return (
                <li key={entry.id}>
                  {entry.href ? (
                    <Link href={entry.href} className="block transition hover:opacity-90">
                      {row}
                    </Link>
                  ) : (
                    row
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </V4Card>

      <div data-testid="journal-studio-workspace-strip">
        <V4Card className="flex items-start gap-3 border-amber-500/20 p-4">
          <TrendingUp className="mt-0.5 size-4 shrink-0 text-amber-300" aria-hidden />
          <div>
            <p className="text-sm font-medium text-white">Learning loop studio</p>
            <p className="text-sm text-white/60">
              Configure fields and review cron in Studio settings. Timeline merges verified trading activity with
              manual lessons.
            </p>
          </div>
        </V4Card>
      </div>
    </div>
  );
}
