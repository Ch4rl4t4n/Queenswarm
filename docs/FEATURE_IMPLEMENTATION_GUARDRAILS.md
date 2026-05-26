# Feature Implementation Guardrails

Updated: 2026-05-22

**Mandatory for every new feature, route, panel, or API surface.**  
Referenced from `docs/ROADMAP.md` and `docs/MISSION_EXECUTION_BACKLOG.md`.

Goal: ship product value **without** re-breaking cockpit speed, scroll performance, or simulate-first safety.

---

## Decision flow

```
Idea → Simulate-first? → Feature flag → Lazy FE chunk → Cached BE → Gate script → Deploy
         ↓ no              ↓ skip live paths
       STOP               ship behind flag until verified
```

---

## Checklist (before merge)

| # | Rule | Why | Example in repo |
|---|------|-----|-----------------|
| 1 | **Simulate-first** — no live upstream without operator approval | Hive philosophy + ban risk | Execution Studio policy, publish pack `simulate_only` |
| 2 | **Feature flag / env** — new surface off until gate green | Safe rollback | `PUBLISH_QUEUE_ENABLED`, `platform_features` |
| 3 | **Lazy FE panel** — no +200 line monolith blocks | Scroll + re-render isolation | `execution-studio-*-panel.tsx` + `dynamic()` |
| 4 | **React.memo + isolated state** — typing in one panel must not re-render siblings | Notifications/webhook perf | `ExecutionStudioNotificationsPanel` |
| 5 | **Single snapshot endpoint** — prefer one bundle over N polls | Cockpit perf | `GET /dashboard/cockpit`, `GET /publish-queue` |
| 6 | **SWR / cache** — staleTime on hot reads; WS delta when live | Fewer redundant requests | `cockpit-swr-keys.ts`, `applyCockpitWsDelta` |
| 7 | **No RSC in client warmers** — never import async Server Components from client chunks | Build/runtime break | Removed `costs-cockpit-page` from chunk warmer |
| 8 | **Gate script** — `./scripts/audit-*-gate.sh` before prod | Regression catch | `audit-publish-pack-gate.sh` |
| 9 | **Tests** — happy + error path on public API | Contract safety | `test_publish_queue_unit.py` |
| 10 | **Audit log** — admin/operator actions structured | Security | structlog with `agent_id`, `task_id` |

---

## Frontend patterns

- **Hot routes:** idle + hover prefetch (`hive-route-prefetch.ts`, `use-route-prefetch.ts`).
- **Heavy charts:** `ViewportLazyMount` + `dynamic(..., { ssr: false })`.
- **Settings tabs:** keep-alive shell (`settings-panel-host.tsx`) — don't remount on tab switch.
- **Desktop shell:** no duplicate top bars ≥1024px — sidebar + canvas only.
- **New section in existing page:** extract to `*-panel.tsx`, import via `dynamic()` from parent.

---

## Backend patterns

- **Parallel I/O:** `asyncio.gather` for independent probes (Command Center).
- **Redis cache** for expensive read-mostly aggregates (atlas, rate limits).
- **Pydantic v2** on every endpoint body/query.
- **JWT** on all operator endpoints except `/health`, `/metrics`, `/docs`.
- **Never** hardcode secrets — Pydantic Settings only.

---

## When adding a new hub tab or settings section

1. Add feature key to `platform_features.py` + `platform-features.ts` if gated.
2. Add route to prefetch map if it's a hot path.
3. Default loading skeleton — lightweight, no layout shift.
4. Run responsive E2E if shell changed: `e2e/responsive-shell.spec.ts`.

---

## References

- `docs/PERFORMANCE_COCKPIT.md` — dashboard telemetry budgets
- `docs/PRODUCTION_AUTOMATION_PHASES.md` — publish lane simulate → approve → live
- `AGENTS.md` — harness philosophy
- Execution Studio panel split — `frontend/components/connectors/execution-studio-*-panel.tsx`
