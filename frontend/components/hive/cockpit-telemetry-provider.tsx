"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import useSWR, { mutate as globalMutate } from "swr";

import { hiveGet } from "@/lib/api";
import {
  type DashboardCockpitBundle,
  mapCockpitSystemLiteToStatus,
} from "@/lib/cockpit-bundle";
import {
  applyCockpitWsDelta,
  applyTaskQueueWsDelta,
  shouldRevalidateCockpitAfterPulse,
  shouldRevalidateTaskQueueAfterPulse,
  type HiveLivePulsePayload,
} from "@/lib/cockpit-ws-delta";
import { COCKPIT_PERF } from "@/lib/cockpit-performance-budget";
import { COCKPIT_POLL_COLONY_TELEMETRY_MS, COCKPIT_POLL_SYSTEM_STATUS_MS } from "@/lib/cockpit-poll-profile";
import { cockpitSwrKeys } from "@/lib/cockpit-swr-keys";
import { DASHBOARD_BOOT_STAGGER_MS } from "@/lib/dashboard-boot-stagger";
import { useCockpitLivePulse } from "@/lib/hooks/use-cockpit-live-pulse";
import {
  useDashboardSummaryPollEnabled,
  useDashboardTelemetryPollEnabled,
} from "@/lib/hooks/use-dashboard-telemetry-poll-enabled";
import { useRouteScopedPollOptions } from "@/lib/hooks/use-route-scoped-poll";
import type { AgentRow, DashboardSummary, SystemStatusPayload, TaskRow } from "@/lib/hive-types";

export interface CockpitTelemetryContextValue {
  agents: AgentRow[];
  recentTasks: TaskRow[];
  systemStatus: SystemStatusPayload | null;
  summary: DashboardSummary | null;
  costWindowUsd: number | null;
  telemetryLoading: boolean;
  wsConnected: boolean;
  refreshAgents: () => Promise<AgentRow[] | undefined>;
  refreshTelemetry: () => Promise<void>;
}

const CockpitTelemetryContext = createContext<CockpitTelemetryContextValue | null>(null);

interface CockpitTelemetryProviderProps {
  readonly children: ReactNode;
  readonly initialAgents?: AgentRow[];
  readonly initialCockpit?: DashboardCockpitBundle | null;
}

function buildCockpitQuery(): string {
  return `dashboard/cockpit?agents_limit=${COCKPIT_PERF.dashboardAgentsLimit}&tasks_limit=${COCKPIT_PERF.recentTasksLimit}`;
}

async function fetchCockpitBundle(): Promise<DashboardCockpitBundle> {
  return hiveGet<DashboardCockpitBundle>(buildCockpitQuery());
}

async function fetchCosts30d(): Promise<number> {
  const body = await hiveGet<{ series?: { spend_usd: number }[] }>("operator/costs/summary?days=30");
  return (body.series ?? []).reduce((sum, row) => sum + (Number(row.spend_usd) || 0), 0);
}

function resolveInitialBundle(
  initialCockpit: DashboardCockpitBundle | null | undefined,
  initialAgents: AgentRow[],
): DashboardCockpitBundle | undefined {
  if (initialCockpit) {
    return initialCockpit;
  }
  if (initialAgents.length === 0) {
    return undefined;
  }
  return {
    generated_at: new Date(0).toISOString(),
    revision: 0,
    agents: initialAgents,
    recent_tasks: [],
    summary: {
      generated_at: new Date(0).toISOString(),
      agents: { total: initialAgents.length, by_status: {}, by_hive_tier: {} },
      tasks: { pending: 0 },
    },
    system_status: {
      agents_total: initialAgents.length,
      agents_running: 0,
      tasks_running: 0,
      tasks_pending: 0,
      llm_grok: false,
      llm_anthropic: false,
    },
  };
}

/** Single SWR-backed telemetry layer for the dashboard cockpit. */
export function CockpitTelemetryProvider({
  children,
  initialAgents = [],
  initialCockpit = null,
}: CockpitTelemetryProviderProps): JSX.Element {
  const telemetryEnabled = useDashboardTelemetryPollEnabled();
  const summaryEnabled = useDashboardSummaryPollEnabled();

  const basePollMs = Math.max(COCKPIT_PERF.minTelemetryPollMs, COCKPIT_POLL_COLONY_TELEMETRY_MS);
  const fallbackBundle = resolveInitialBundle(initialCockpit, initialAgents);
  const mutateRef = useRef<() => Promise<DashboardCockpitBundle | undefined>>(async () => undefined);
  const bundleRef = useRef<DashboardCockpitBundle | undefined>(fallbackBundle);

  const wsConnected = useCockpitLivePulse({
    enabled: telemetryEnabled,
    onPulse: (pulse: HiveLivePulsePayload) => {
      const current = bundleRef.current;
      if (!current || shouldRevalidateCockpitAfterPulse(current, pulse)) {
        void mutateBundle(undefined, { revalidate: true });
      } else {
        void mutateBundle(applyCockpitWsDelta(current, pulse), { revalidate: false });
      }

      if (pulse.task_queue_strip) {
        const strip = pulse.task_queue_strip;
        if (shouldRevalidateTaskQueueAfterPulse(strip)) {
          void globalMutate(cockpitSwrKeys.taskQueue(120));
        } else {
          void globalMutate(
            cockpitSwrKeys.taskQueue(120),
            (cached) => applyTaskQueueWsDelta(cached, strip),
            { revalidate: false },
          );
        }
      }
    },
  });

  const telemetryPollMs = useMemo(() => {
    if (!telemetryEnabled) {
      return 0;
    }
    if (wsConnected) {
      return Math.max(COCKPIT_PERF.wsConnectedPollMs, basePollMs);
    }
    return basePollMs;
  }, [telemetryEnabled, wsConnected, basePollMs]);

  const telemetryPollBase = useRouteScopedPollOptions(telemetryPollMs, "/");
  const telemetryPoll = {
    ...telemetryPollBase,
    refreshInterval: telemetryEnabled ? telemetryPollBase.refreshInterval : 0,
  };

  const {
    data: bundle,
    isLoading: bundleLoading,
    mutate: mutateBundle,
  } = useSWR<DashboardCockpitBundle>(
    telemetryEnabled
      ? cockpitSwrKeys.bundle(COCKPIT_PERF.dashboardAgentsLimit, COCKPIT_PERF.recentTasksLimit)
      : null,
    fetchCockpitBundle,
    {
      ...telemetryPoll,
      fallbackData: fallbackBundle,
      keepPreviousData: true,
    },
  );

  useEffect(() => {
    bundleRef.current = bundle;
  }, [bundle]);

  useEffect(() => {
    mutateRef.current = () => mutateBundle(undefined, { revalidate: true });
  }, [mutateBundle]);

  const summaryPollBase = useRouteScopedPollOptions(
    summaryEnabled ? COCKPIT_POLL_SYSTEM_STATUS_MS : 0,
    "/",
  );
  const summaryPoll = {
    ...summaryPollBase,
    refreshInterval: summaryEnabled ? summaryPollBase.refreshInterval : 0,
  };

  const { data: costWindowUsd = null } = useSWR<number>(
    summaryEnabled ? cockpitSwrKeys.costs30d() : null,
    fetchCosts30d,
    {
      ...summaryPoll,
      keepPreviousData: true,
      dedupingInterval: 30_000,
    },
  );

  const agents = bundle?.agents ?? initialAgents;
  const recentTasks = useMemo(() => bundle?.recent_tasks ?? [], [bundle?.recent_tasks]);
  const summary = bundle?.summary ?? null;
  const systemStatus = bundle?.system_status ? mapCockpitSystemLiteToStatus(bundle.system_status) : null;

  const refreshAgents = useCallback(async () => {
    const next = await mutateBundle();
    return next?.agents;
  }, [mutateBundle]);

  const refreshTelemetry = useCallback(async () => {
    await mutateBundle();
  }, [mutateBundle]);

  const telemetryLoading = telemetryEnabled && bundleLoading && agents.length === 0;

  const value = useMemo<CockpitTelemetryContextValue>(
    () => ({
      agents,
      recentTasks,
      systemStatus,
      summary,
      costWindowUsd,
      telemetryLoading,
      wsConnected,
      refreshAgents,
      refreshTelemetry,
    }),
    [
      agents,
      recentTasks,
      systemStatus,
      summary,
      costWindowUsd,
      telemetryLoading,
      wsConnected,
      refreshAgents,
      refreshTelemetry,
    ],
  );

  return <CockpitTelemetryContext.Provider value={value}>{children}</CockpitTelemetryContext.Provider>;
}

export function useCockpitTelemetry(): CockpitTelemetryContextValue {
  const ctx = useContext(CockpitTelemetryContext);
  if (!ctx) {
    throw new Error("useCockpitTelemetry must be used within CockpitTelemetryProvider");
  }
  return ctx;
}

/** Stagger hint for first telemetry paint — re-export for boot ordering docs. */
export const COCKPIT_TELEMETRY_BOOT_MS = DASHBOARD_BOOT_STAGGER_MS.colonyTelemetry;
