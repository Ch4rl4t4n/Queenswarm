"use client";

import { ExternalLink } from "lucide-react";
import dynamic from "next/dynamic";
import { memo, useCallback, useState } from "react";
import { toast } from "sonner";

import { ExecutionRecentActivityGrid } from "@/components/connectors/execution-recent-activity-grid";
import type { ConnectorChartDatum } from "@/components/connectors/execution-studio-connector-chart";
import type { ActivityTimeSeriesDatum } from "@/components/connectors/execution-studio-telemetry-timeseries-chart";
import { ViewportLazyMount } from "@/components/hive/viewport-lazy-mount";
import { V4Badge } from "@/components/ui/v4";
import { HiveApiError, hiveDelete } from "@/lib/api";

const chartSkeleton = () => <div className="h-56 w-full animate-pulse rounded-xl bg-white/5" aria-hidden />;

const ExecutionStudioTelemetryTimeseriesChart = dynamic(
  () =>
    import("@/components/connectors/execution-studio-telemetry-timeseries-chart").then((mod) => ({
      default: mod.ExecutionStudioTelemetryTimeseriesChart,
    })),
  { ssr: false, loading: chartSkeleton },
);

const ExecutionStudioConnectorChart = dynamic(
  () =>
    import("@/components/connectors/execution-studio-connector-chart").then((mod) => ({
      default: mod.ExecutionStudioConnectorChart,
    })),
  { ssr: false, loading: chartSkeleton },
);

export interface StudioActivity {
  event_type: string;
  message: string;
  at: string;
  payload?: Record<string, unknown>;
}

export interface MediaRegistryItem {
  template_id: string;
  slug: string;
  display_name: string;
  status: string;
  is_active: boolean;
  tools_count: number;
  agent_usage?: string | null;
  cost_tier?: string;
  doc_url?: string | null;
}

export interface MediaRegistry {
  pack_id: string;
  label: string;
  items: MediaRegistryItem[];
}

export interface ActivityTelemetry {
  total_events: number;
  by_event_type: Record<string, number>;
  by_connector?: Record<string, number>;
  connector_cost_blocks?: Record<string, number>;
  connector_chart?: ConnectorChartDatum[];
  activity_time_series?: ActivityTimeSeriesDatum[];
  tool_executes: number;
  browser_steps: number;
  proposals_created: number;
  maintainer_runs: number;
  cost_tier_blocks: number;
  window_limit: number;
}

export interface ExecutionStudioAnalyticsPanelProps {
  activityTelemetry: ActivityTelemetry | undefined;
  recentActivity: StudioActivity[] | undefined;
  mediaRegistry: MediaRegistry | undefined;
  onError: (message: string | null) => void;
  onReloadOverview: () => Promise<void>;
}

function ExecutionStudioAnalyticsPanelInner({
  activityTelemetry,
  recentActivity,
  mediaRegistry,
  onError,
  onReloadOverview,
}: ExecutionStudioAnalyticsPanelProps) {
  const [clearBusy, setClearBusy] = useState(false);

  const clearRecentActivity = useCallback(async () => {
    setClearBusy(true);
    onError(null);
    try {
      await hiveDelete<{ cleared: number }>("execution-studio/activity");
      toast.success("Recent activity cleared");
      await onReloadOverview();
    } catch (exc) {
      onError(exc instanceof HiveApiError ? exc.message : "Unable to clear recent activity.");
    } finally {
      setClearBusy(false);
    }
  }, [onError, onReloadOverview]);

  return (
    <>
      {activityTelemetry ? (
        <div className="grid shrink-0 gap-2 md:grid-cols-5">
          <article className="qs-bubble-stat px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-(--qs-text-4)">Tool runs</p>
            <p className="font-mono text-lg text-cyan">{activityTelemetry.tool_executes}</p>
          </article>
          <article className="qs-bubble-stat px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-(--qs-text-4)">Browser steps</p>
            <p className="font-mono text-lg text-cyan">{activityTelemetry.browser_steps}</p>
          </article>
          <article className="qs-bubble-stat px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-(--qs-text-4)">Proposals</p>
            <p className="font-mono text-lg text-pollen">{activityTelemetry.proposals_created}</p>
          </article>
          <article className="qs-bubble-stat px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-(--qs-text-4)">Maintainer</p>
            <p className="font-mono text-lg text-(--qs-green)">{activityTelemetry.maintainer_runs}</p>
          </article>
          <article className="qs-bubble-stat qs-bubble--tint-magenta px-3 py-2">
            <p className="text-[10px] uppercase tracking-wider text-(--qs-text-4)">Cost blocks</p>
            <p className="font-mono text-lg text-magenta">{activityTelemetry.cost_tier_blocks}</p>
          </article>
        </div>
      ) : null}

      {activityTelemetry?.activity_time_series && activityTelemetry.activity_time_series.length > 0 ? (
        <div className="qs-bubble shrink-0 space-y-2 p-4">
          <p className="text-sm font-semibold text-(--qs-text)">Activity over time (hourly)</p>
          <ViewportLazyMount>
            <ExecutionStudioTelemetryTimeseriesChart data={activityTelemetry.activity_time_series} />
          </ViewportLazyMount>
        </div>
      ) : null}

      {activityTelemetry?.connector_chart && activityTelemetry.connector_chart.length > 0 ? (
        <div className="qs-bubble shrink-0 space-y-2 p-4">
          <p className="text-sm font-semibold text-(--qs-text)">Connector activity chart</p>
          <ViewportLazyMount>
            <ExecutionStudioConnectorChart data={activityTelemetry.connector_chart} />
          </ViewportLazyMount>
        </div>
      ) : null}

      {activityTelemetry?.by_connector && Object.keys(activityTelemetry.by_connector).length > 0 ? (
        <div className="qs-bubble shrink-0 p-4">
          <p className="text-sm font-semibold text-(--qs-text)">Per-connector activity</p>
          <ul className="mt-2 grid gap-2 md:grid-cols-2">
            {Object.entries(activityTelemetry.by_connector).map(([slug, count]) => (
              <li key={slug} className="qs-bubble-inner flex items-center justify-between px-3 py-2 text-xs">
                <span className="font-mono text-cyan">{slug}</span>
                <span className="text-(--qs-text-2)">
                  {count} runs
                  {(activityTelemetry.connector_cost_blocks?.[slug] ?? 0) > 0 ? (
                    <span className="ml-2 text-magenta">
                      · {activityTelemetry.connector_cost_blocks?.[slug]} blocked
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <ExecutionRecentActivityGrid
        items={recentActivity ?? []}
        clearBusy={clearBusy}
        onClear={() => void clearRecentActivity()}
      />

      {(mediaRegistry?.items.length ?? 0) > 0 ? (
        <div className="qs-bubble qs-bubble--tint-magenta shrink-0 space-y-3 p-4">
          <p className="text-sm font-semibold text-(--qs-text)">{mediaRegistry?.label ?? "Media & generation"}</p>
          <p className="text-xs text-(--qs-text-3)">
            Image, copy, and creative routers — assign to content_creation or Super Tool Routers.
          </p>
          <div className="grid gap-2 md:grid-cols-2">
            {mediaRegistry?.items.map((item) => (
              <article key={item.template_id} className="qs-bubble-inner p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-(--qs-text)">{item.display_name}</p>
                  <V4Badge tone={item.is_active ? "ok" : item.status === "not_installed" ? "warn" : "info"}>
                    {item.is_active ? "active" : item.status.replaceAll("_", " ")}
                  </V4Badge>
                </div>
                <p className="mt-1 text-[10px] text-(--qs-text-3)">{item.agent_usage ?? "Creative / media MCP tools"}</p>
                <p className="mt-2 font-mono text-[10px] text-(--qs-text-4)">
                  {item.tools_count} tools · {item.cost_tier ?? "medium"} cost
                </p>
                {item.doc_url ? (
                  <a
                    href={item.doc_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-flex items-center gap-1 text-[10px] text-cyan hover:underline"
                  >
                    Docs <ExternalLink className="h-3 w-3" aria-hidden />
                  </a>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}

export const ExecutionStudioAnalyticsPanel = memo(ExecutionStudioAnalyticsPanelInner);
