/**
 * Cockpit performance budgets — keep boot bursts and poll payloads bounded.
 * Tune via code review when adding new dashboard widgets.
 */

export const COCKPIT_PERF = {
  /** Max recommended parallel API calls during dashboard boot (stagger enforces this). */
  maxBootParallelRequests: 6,
  /** Agent roster limit on dashboard (honeycomb + filters). Full roster on /agents. */
  dashboardAgentsLimit: 96,
  /** Full agents page / spawn flows. */
  fullAgentsLimit: 200,
  /** Recent tasks strip on dashboard chrome. */
  recentTasksLimit: 10,
  /** List view renders this many rows before "Show more" (dashboard cap). */
  listInitialRender: 40,
  /** Grid honeycomb cap on full roster page before "Show more". */
  gridInitialRender: 48,
  /** Estimated row height for virtual list (px). */
  listVirtualRowPx: 88,
  /** Gap between virtual rows — matches `space-y-3` (px). */
  listVirtualRowGapPx: 12,
  /** Extra rows rendered above/below viewport. */
  listVirtualOverscan: 8,
  /** Task queue rows included in WS strip merge. */
  taskQueueWsStripLimit: 20,
  /** Minimum poll interval for dashboard telemetry (ms). */
  minTelemetryPollMs: 10_000,
  /** Poll fallback when WebSocket live pulse is connected (ms). */
  wsConnectedPollMs: 60_000,
} as const;

export type CockpitPerfBudget = typeof COCKPIT_PERF;
