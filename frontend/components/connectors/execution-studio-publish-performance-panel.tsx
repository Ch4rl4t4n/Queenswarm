"use client";

import { BarChart3 } from "lucide-react";
import { memo, useCallback, useEffect, useState } from "react";

import { HiveRefreshButton } from "@/components/hive/hive-refresh-button";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveGet } from "@/lib/api";
interface PublishChannelStats {
  channel: string;
  simulate_ok: number;
  live_ok: number;
  queue_approved: number;
  rejected: number;
}

interface PublishPerformanceInsight {
  id: string;
  label: string;
  detail: string;
  priority: "high" | "medium" | "low";
}

interface PublishPerformanceSnapshot {
  enabled: boolean;
  generated_at: string;
  window_days: number;
  totals: Record<string, number>;
  by_channel: PublishChannelStats[];
  simulate_success_rate_pct: number;
  live_posts: number;
  queue_approval_rate_pct: number;
  insights: PublishPerformanceInsight[];
  recent_highlights: string[];
  hook_winners?: HookWinner[];
}

interface HookWinner {
  channel: string;
  winning_style: string;
  sample_hook: string;
  pack_count: number;
  confidence: number;
}

export interface ExecutionStudioPublishPerformancePanelProps {
  onError: (message: string | null) => void;
}

function insightTone(priority: PublishPerformanceInsight["priority"]): "ok" | "warn" | "err" | "info" {
  if (priority === "high") return "err";
  if (priority === "medium") return "warn";
  return "info";
}

function ExecutionStudioPublishPerformancePanelInner({ onError }: ExecutionStudioPublishPerformancePanelProps) {
  const [snapshot, setSnapshot] = useState<PublishPerformanceSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    onError(null);
    try {
      const data = await hiveGet<PublishPerformanceSnapshot>("publish-performance");
      setSnapshot(data);
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Failed to load publish performance.");
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !snapshot) {
    return <div className="qs-bubble shrink-0 min-h-[8rem] animate-pulse bg-white/5 p-4" aria-hidden />;
  }

  if (!snapshot?.enabled) {
    return null;
  }

  return (
    <div id="publish-performance" className="qs-bubble qs-bubble--tint-cyan shrink-0 space-y-3 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold text-(--qs-text)">
            <BarChart3 className="h-4 w-4 text-cyan" aria-hidden />
            Publish Performance
          </p>
          <p className="mt-1 text-xs text-(--qs-text-3)">
            Last {snapshot.window_days} days — simulate rate, live posts, channel breakdown.
          </p>
        </div>
        <HiveRefreshButton busy={loading} onClick={() => void load()} />
      </div>

      <div className="flex flex-wrap gap-2 font-mono text-[10px]">
        <V4Badge tone={snapshot.simulate_success_rate_pct >= 80 ? "ok" : "warn"}>
          Simulate {snapshot.simulate_success_rate_pct}%
        </V4Badge>
        <V4Badge tone="info">{snapshot.live_posts} live</V4Badge>
        <V4Badge tone="info">{snapshot.totals.queue_approved ?? 0} approved</V4Badge>
        <V4Badge tone={snapshot.totals.queue_rejected ? "err" : "ok"}>
          {snapshot.totals.queue_rejected ?? 0} rejected
        </V4Badge>
      </div>

      {snapshot.by_channel.length > 0 ? (
        <ul className="space-y-1 text-xs">
          {snapshot.by_channel.slice(0, 6).map((row) => (
            <li key={row.channel} className="flex flex-wrap justify-between gap-2 rounded bg-black/20 px-2 py-1">
              <span className="uppercase text-cyan">{row.channel}</span>
              <span className="font-mono text-(--qs-text-3)">
                sim {row.simulate_ok} · live {row.live_ok} · approved {row.queue_approved}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-(--qs-text-3)">No publish events yet — approve packs and run simulate.</p>
      )}

      {snapshot.hook_winners && snapshot.hook_winners.length > 0 ? (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-(--qs-text-3)">Hook winners</p>
          <ul className="space-y-1 text-xs">
            {snapshot.hook_winners.slice(0, 4).map((row) => (
              <li key={`${row.channel}-${row.winning_style}`} className="rounded bg-black/20 px-2 py-1">
                <span className="uppercase text-pollen">{row.channel}</span>
                <span className="text-(--qs-text-3)"> · {row.winning_style}</span>
                {row.sample_hook ? (
                  <p className="mt-0.5 truncate text-[11px] text-(--qs-muted)">{row.sample_hook}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {snapshot.insights.length > 0 ? (
        <ul className="space-y-2">
          {snapshot.insights.map((insight) => (
            <li key={insight.id} className="rounded border border-(--qs-border)/60 bg-black/20 px-3 py-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-medium text-(--qs-text)">{insight.label}</span>
                <V4Badge tone={insightTone(insight.priority)}>{insight.priority}</V4Badge>
              </div>
              <p className="mt-0.5 text-[11px] text-(--qs-muted)">{insight.detail}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export const ExecutionStudioPublishPerformancePanel = memo(ExecutionStudioPublishPerformancePanelInner);
