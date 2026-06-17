"use client";

import Link from "next/link";
import { CalendarClock, CheckCircle2, Clock, Send } from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useState } from "react";

import { HivePanelSectionSkeleton } from "@/components/hive/hive-panel-section-skeleton";
import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge, V4Card, V4CardHeader } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
import { COCKPIT_POLL_BOARD_MS } from "@/lib/cockpit-poll-profile";
import { useIntervalWhenVisible } from "@/lib/hooks/use-interval-when-visible";
import { cn } from "@/lib/utils";

type MarketingTeamEntryStatus = "pending" | "approved" | "scheduled" | "published" | "rejected";

interface MarketingTeamCalendarEntry {
  id: string;
  title: string;
  channel: string;
  status: MarketingTeamEntryStatus;
  scheduled_at: string | null;
  body_preview: string;
  media_kind: string | null;
  href: string;
}

interface MarketingTeamChannelSummary {
  channel: string;
  label: string;
  active: boolean;
  live_allowed: boolean;
}

interface MarketingTeamSnapshot {
  enabled: boolean;
  generated_at: string;
  horizon_days: number;
  calendar_entries: MarketingTeamCalendarEntry[];
  unscheduled_approved_count: number;
  queue_pending_count: number;
  queue_approved_count: number;
  channels_ready_count: number;
  channels_total: number;
  channel_summaries: MarketingTeamChannelSummary[];
  live_publish_enabled: boolean;
  scheduled_publish_enabled: boolean;
  links: Record<string, string>;
  operator_hint: string;
}

const STATUS_TONE: Record<MarketingTeamEntryStatus, string> = {
  pending: "border-magenta-300/40 bg-magenta-300/10 text-magenta-100",
  approved: "border-cyan-300/40 bg-cyan-300/10 text-cyan-100",
  scheduled: "border-pollen/40 bg-pollen/10 text-pollen",
  published: "border-green-300/40 bg-green-300/10 text-green-100",
  rejected: "border-red-300/40 bg-red-300/10 text-red-100",
};

function formatSlot(iso: string | null): string {
  if (!iso) {
    return "Unscheduled";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Unscheduled";
  }
  return date.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function groupEntriesByDay(entries: MarketingTeamCalendarEntry[]): Map<string, MarketingTeamCalendarEntry[]> {
  const groups = new Map<string, MarketingTeamCalendarEntry[]>();
  for (const entry of entries) {
    const key = entry.scheduled_at
      ? new Date(entry.scheduled_at).toISOString().slice(0, 10)
      : "unscheduled";
    const bucket = groups.get(key) ?? [];
    bucket.push(entry);
    groups.set(key, bucket);
  }
  return groups;
}

function MarketingTeamCalendarPanelInner(): JSX.Element {
  const [snapshot, setSnapshot] = useState<MarketingTeamSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const data = await hiveGet<MarketingTeamSnapshot>("operator/marketing-team");
      setSnapshot(data);
      setErr(null);
    } catch (e) {
      setErr(e instanceof HiveApiError ? e.message : "Marketing Team snapshot unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useIntervalWhenVisible(() => void reload(), COCKPIT_POLL_BOARD_MS);

  const dayGroups = useMemo(
    () => groupEntriesByDay(snapshot?.calendar_entries ?? []),
    [snapshot?.calendar_entries],
  );

  if (loading && !snapshot) {
    return <HivePanelSectionSkeleton label="Loading Marketing Team calendar" minHeightClass="min-h-[14rem]" />;
  }

  if (!snapshot?.enabled) {
    return (
      <V4Card>
        <V4CardHeader kicker="Calendar" title="Marketing Team" description="Module disabled on this deployment." />
      </V4Card>
    );
  }

  return (
    <div className="flex flex-col gap-3" data-testid="marketing-team-calendar">
      <div className="grid gap-3 md:max-lg:grid-cols-2 lg:grid-cols-4">
        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Queue"
            title={`${snapshot.queue_pending_count} pending`}
            description={`${snapshot.queue_approved_count} approved · simulate-first`}
            actions={<HiveRefreshButton busy={loading} onClick={() => void reload()} />}
          />
          <div className="px-4 pb-4">
            <Link href={snapshot.links.queue ?? "#publish-queue"} className="qs-btn qs-btn--ghost qs-btn--sm">
              Open publish queue
            </Link>
          </div>
        </V4Card>
        <V4Card className="md:max-lg:col-span-1">
          <V4CardHeader
            kicker="Channels"
            title={`${snapshot.channels_ready_count}/${snapshot.channels_total} ready`}
            description={snapshot.live_publish_enabled ? "Live publish enabled" : "Simulate-only until OAuth + live flag"}
          />
          <ul className="space-y-1 px-4 pb-4">
            {snapshot.channel_summaries.slice(0, 4).map((row) => (
              <li key={row.channel} className="flex items-center justify-between text-xs text-(--qs-text-2)">
                <span>{row.label}</span>
                <V4Badge tone={row.active ? "ok" : "info"}>{row.active ? "OAuth" : "Setup"}</V4Badge>
              </li>
            ))}
          </ul>
        </V4Card>
        <V4Card className="md:max-lg:col-span-2 lg:col-span-2">
          <V4CardHeader
            kicker="Operator"
            title="Next actions"
            description={snapshot.operator_hint}
          />
          <div className="flex flex-wrap gap-2 px-4 pb-4">
            <Link href={snapshot.links.queue ?? "#"} className="qs-btn qs-btn--primary qs-btn--sm gap-1">
              <CheckCircle2 className="size-3.5" aria-hidden />
              Review queue
            </Link>
            <Link href={snapshot.links.publish ?? "#"} className="qs-btn qs-btn--ghost qs-btn--sm gap-1">
              <Send className="size-3.5" aria-hidden />
              Social publish
            </Link>
            <Link href={snapshot.links.integrations ?? "/integrations"} className="qs-btn qs-btn--ghost qs-btn--sm">
              Connect OAuth
            </Link>
          </div>
        </V4Card>
      </div>

      {err ? (
        <p className="text-xs text-[#FF3366]" role="alert">
          {err}
        </p>
      ) : null}

      <V4Card>
        <V4CardHeader
          kicker="Calendar"
          title={`Next ${snapshot.horizon_days} days`}
          description={
            snapshot.scheduled_publish_enabled
              ? "Approved packs with scheduled_at auto-simulate via Celery tick."
              : "Set scheduled_at on publish packs for automated simulate."
          }
        />
        <div className="space-y-4 px-4 pb-4">
          {snapshot.unscheduled_approved_count > 0 ? (
            <p className="flex items-center gap-2 text-xs text-pollen">
              <Clock className="size-3.5" aria-hidden />
              {snapshot.unscheduled_approved_count} approved pack(s) without schedule
            </p>
          ) : null}
          {[...dayGroups.entries()].map(([dayKey, entries]) => (
            <div key={dayKey}>
              <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-(--qs-text-3)">
                <CalendarClock className="size-3.5" aria-hidden />
                {dayKey === "unscheduled" ? "Unscheduled" : dayKey}
              </p>
              <ul className="space-y-2">
                {entries.map((entry) => (
                  <li key={entry.id}>
                    <Link
                      href={entry.href}
                      className={cn(
                        "flex flex-col gap-1 rounded-xl border px-3 py-2 transition hover:border-cyan/40",
                        STATUS_TONE[entry.status],
                      )}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-medium">{entry.title}</span>
                        <span className="text-[11px] uppercase tracking-wide">{entry.status}</span>
                      </div>
                      <p className="text-xs opacity-80">
                        {entry.channel} · {formatSlot(entry.scheduled_at)}
                      </p>
                      {entry.body_preview ? (
                        <p className="line-clamp-2 text-xs opacity-70">{entry.body_preview}</p>
                      ) : null}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
          {snapshot.calendar_entries.length === 0 ? (
            <p className="text-sm text-(--qs-text-3)">
              No publish packs yet — run a marketing session in Agents, verify critic, then approve in queue.
            </p>
          ) : null}
        </div>
      </V4Card>
    </div>
  );
}

export const MarketingTeamCalendarPanel = memo(MarketingTeamCalendarPanelInner);
