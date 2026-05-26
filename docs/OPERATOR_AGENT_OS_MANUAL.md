# Operator — Agent OS (P8 autonomy layer)

Unified autonomy snapshot: **cross-swarm recipe transfer**, **imitation v2**, **overnight behavioral proposals**, and **analysis consensus**.

## Where

- **Settings → AI · harness → My 3 Bees** — **Agent OS** panel (under Operator Loop)
- **API:** `GET /api/v1/agent-os` · `POST /api/v1/agent-os/analysis/consensus`

## Daily use

1. Refresh **Agent OS** after overnight Dump & Sleep
2. Review **behavioral proposals** → merge into Settings harness instructions
3. When imitation shows **3+ verified outcomes**, copy suggested recipe (simulate first)
4. Apply **cross-swarm** suggestions (trading → marketing)
5. Paper trading auto-creates **trade→content** drafts in Publish Queue after fills

## Swarm templates (Swarm Builder)

- **Polymarket Trading Swarm** — Forager → Analysis → Risk → Paper Executor
- **Content Flywheel 2.0** — research → recipe match → hooks → performance loop

## Cron

| Task | Time | Purpose |
|------|------|---------|
| `hive.trading_overnight_review_tick` | 06:00 UTC | Trading P&L digest |
| `hive.operator_loop_morning_tick` | 07:30 UTC | Morning Telegram |
| `hive.morning_publish_pipeline_tick` | 08:00 UTC | Publish routines |

## Flags

```bash
AGENT_OS_ENABLED=true
ANALYSIS_SWARM_ENABLED=true
TRADE_TO_CONTENT_ENABLED=true
CROSS_SWARM_KNOWLEDGE_ENABLED=true
IMITATION_V2_ENABLED=true
DREAMING_BEHAVIORAL_PROPOSALS_ENABLED=true
TRADING_OVERNIGHT_REVIEW_ENABLED=true
```

## Gate

```bash
./scripts/audit-agent-os-p8-gate.sh
```
