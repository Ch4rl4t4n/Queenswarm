# Cockpit performance — audit & playbook

Baseline audit (dashboard `/`) before shared telemetry layer:

| Issue | Symptom | Mitigation |
|-------|---------|------------|
| Duplicate polls | Colony console + widgets each hit API | `CockpitTelemetryProvider` + SWR keys in `cockpit-swr-keys.ts` |
| Large payloads | `agents?limit=200` every ~8s | Dashboard uses `COCKPIT_PERF.dashboardAgentsLimit` (96) |
| Background churn | Polls while tab hidden | `useSwrVisiblePollOptions` + `useIntervalWhenVisible` |
| Layout flyout open | Full canvas still polling | `useDashboardTelemetryPollEnabled` gates polls |
| List re-renders | 100+ agent rows in list mode | Dashboard cap at 40 + "Show more"; `/agents` uses `@tanstack/react-virtual` |
| Parallel boot requests | 4–5 endpoints on every poll | `GET /dashboard/cockpit` single bundle |

## Architecture

```
ColonyConsole
  └── CockpitTelemetryProvider (SWR)
        ├── GET /dashboard/cockpit (agents + tasks + summary + lite system)
        │     └── useCockpitLivePulse → /ws/live hive.snapshot → mutate on revision
        └── operator/costs/summary 30d (slower, separate)
```

Widget sections (`TaskQueueSection`, `SwarmBoardSection`) use SWR dedupe — no duplicate in-flight requests for the same key.

When WebSocket live pulse is connected, telemetry poll fallback lengthens to `COCKPIT_PERF.wsConnectedPollMs` (60s). Snapshots patch the SWR cache via `applyCockpitWsDelta` (agent status + KPI counts) without a full refetch when the roster size is unchanged.

## WS delta patch flow

```
/ws/live hive.snapshot
  ├── revision (dedupe)
  ├── system_status (lite gauges)
  ├── agent_deltas[] (running + recently updated bees, max 48)
  ├── recent_tasks[] (latest 10 — dashboard strip)
  └── task_queue_strip (counts + 20 rows — task queue widget)
        └── CockpitTelemetryProvider
              ├── applyCockpitWsDelta → cockpit bundle (no HTTP)
              └── applyTaskQueueWsDelta → task queue SWR (no HTTP)
                    └── full refetch only when roster total changes or strip empty
```

## Performance budgets

See `frontend/lib/cockpit-performance-budget.ts`:

- Boot parallel requests ≤ 6 (enforced by `dashboard-boot-stagger.ts`)
- Dashboard telemetry poll ≥ 10s (`COCKPIT_POLL_COLONY_TELEMETRY_MS`)
- WS-connected poll fallback 60s
- Full agent roster only on `/agents` (limit 200) with virtual list in list view

## Measuring regressions

1. Chrome DevTools → Network: count requests in first 10s on `/`
2. Performance tab: main-thread long tasks during telemetry refresh
3. React Profiler: `ColonyConsoleInner` / `AgentsLiveSection` render time

## Next increments

- True 2D grid virtualizer for honeycomb at 200+ cards (if cap + show-more is insufficient)
