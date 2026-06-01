# Four-Lane Solo Operator Model

Updated: 2026-05-29

**Canonical operator model** for solo tenants on queenswarm.love. Replaces sprawl from automatic Virtual Company department bootstrap.

## Why four lanes?

| Problem (old) | Fix (four lanes) |
|---------------|------------------|
| 16+ generic routines (Sales, Finance, PO…) | **4 missions** with clear deliverables |
| Agents without project briefs | Each lane has **goal template + foragers + schedule** |
| Cannot run parallel work | Lanes run **independently** via Celery + foragers |
| No single control surface | **Agentic OS → Lanes** — pause/resume/bootstrap |

## The four lanes

### Lane A — Najman Marketing (`marketing_najman`)

- **Mission:** Year-round CZ marketing for Rodinné včelařství Najman
- **Schedule:** Mon/Wed/Fri 09:00 UTC (`0 9 * * 1,3,5`)
- **Forager:** Vcelarstvi Competitor Intel
- **Output:** Digest report → approve → Tasks / publish simulate queue
- **Memory:** Curated harness block `Najman Marketing Colony`

### Lane B — Tech SCV (`tech_scv`)

- **Mission:** Daily platform improvement proposals (swarm, harness, MCP)
- **Schedule:** Daily 07:30 UTC + Queen Maintainer weekly
- **Foragers:** X Intel, YouTube Intel (tech sources)
- **Output:** 3 upgrade proposals → **Innovation Lab** → Approve → Implement → **GitHub PR**

### Lane C — E-shop Research (`eshop_research`)

- **Mission:** beebrdy.cz / WooCommerce benchmark vs CZ/SK competitors
- **Schedule:** Tue/Thu 10:00 UTC
- **Forager:** Najman E-shop Intel (RSS competitor blogs)
- **Output:** UX/SEO/conversion digest → approve → redesign brief

### Lane D — Automation Factory (`automation`)

- **Mission:** Turn approved digests into routines/tasks
- **Schedule:** **Manual only** (no auto-cron)
- **Trigger:** After you approve Lane A/B/C outputs
- **Output:** Task rows + optional Maintainer handoff

## Daily operator loop (5 minutes)

Operator: **Jakub Chvostek** (Queenswarm) helping **Najman family** client web/social work.

1. Open **[Agentic OS → Lanes](/agentic-os#lanes)**
2. Review overnight forager ingest in **Knowledge → HiveMind**
3. **Agents → Sessions** — auto-approve ON for routine digests; manual only for critical PR/billing
4. **Innovation** tab — approve/implement tech proposals (Lane B)
5. **Clear filtered** stuck `running` sessions if count > 10

## Weekly rhythm (Jakub · Najman client)

| Day | Focus |
|-----|--------|
| Mon AM | Lanes + Digest inbox → Najman marketing digest → Tasks |
| Wed | Same + Innovation (Tech SCV proposals) |
| Tue/Thu | E-shop research digest (beebrdy.cz) |
| Fri | Run Automation Factory if A/C items approved |
| Daily | 2 min Sessions + Tasks priority |

## Bootstrap (once)

```bash
./scripts/operator-four-lane-provision.sh
```

Or in UI: **Agentic OS → Lanes → Bootstrap lanes**

This will:

1. Pause all routines **without** `four_lane_id` tag
2. Create/retag four lane routines
3. Bind foragers (incl. Najman E-shop Intel)
4. Run Najman brand pack seed (harness + competitor forager)

API:

- `GET /api/v1/solo-operator/four-lanes` — snapshot
- `POST /api/v1/solo-operator/four-lanes/bootstrap` — `{ "pause_legacy": true }`
- `PATCH /api/v1/solo-operator/four-lanes/{lane_id}/active` — `{ "active": true|false }`
- `GET /api/v1/solo-operator/four-lanes/digest-inbox` — pending digests
- `POST /api/v1/solo-operator/four-lanes/digest-inbox/{session_id}/promote` — approve + create task

## Digest Inbox (FL5)

Under **Agentic OS → Lanes**, the **Digest Inbox** lists recent four-lane sessions:

1. Review excerpt inline
2. **→ Task** — approves session + creates Tasks row (marketing/e-shop)
3. **Tech SCV** — use Innovation Lab instead of task promote

Cleanup stuck sessions:

```bash
docker exec queenswarm_prod-backend-1 python scripts/cleanup_stuck_sessions.py --all-stuck --older-than-hours 24
```

## SOLO_MODE guard (FL6)

When `SOLO_MODE_ENABLED=true`, Virtual Company `build-department-swarm` and `build-all-departments` API calls are **rejected**. Use four-lane bootstrap instead.

- All lanes default **simulate-first** — no live publish/deploy without approval gates
- Queen Maintainer remains **PR-only** — never writes to `main`
- Denylist unchanged (`.env`, billing, prod compose)
- Bootstrap requires authenticated dashboard user (tenant-scoped)

## Deprecated (do not re-enable for solo)

- Virtual Company auto department routines (Sales waterfall, Finance, Bank PO, Digital ops, generic E-shop ops)
- Solo operator "My 3 Bees" as primary model — use **Four Lanes** instead (trio still works but is legacy)
- 16-routine sprawl from `operator-agentic-os-setup` without lane tagging

## Related docs

- [`docs/SOLO_OPERATOR_MODE.md`](SOLO_OPERATOR_MODE.md)
- [`docs/harness/QUEEN_MAINTAINER_INSTRUCTIONS.md`](harness/QUEEN_MAINTAINER_INSTRUCTIONS.md)
- Manual: `/manual#four-lanes`
