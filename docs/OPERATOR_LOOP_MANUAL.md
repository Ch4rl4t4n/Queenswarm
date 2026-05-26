# Operator Loop — daily command center

Unified morning/evening snapshot for solo operators: **Overnight Dump & Sleep**, **Morning Brief**, **Publish Queue**, **Publish Onboarding**, and **Trading Cockpit** — plus prioritized actions and optional Telegram digest.

## Where to find it

- **Settings → AI · harness → My 3 Bees** — `Operator Loop` panel at top of solo preset section
- **API:** `GET /api/v1/solo-operator/operator-loop` (JWT)

## Daily workflow

### Evening (5 min)

1. Open **Ballroom → Dump & Sleep**
2. Upload notes, screenshots, or files from the day
3. Let overnight batch complete — morning brief + stalled signals feed Operator Loop

### Morning (10 min)

1. Open **Settings → harness** — refresh **Operator Loop**
2. Work through **Next actions** (high → medium → low):
   - Approve publish packs in **Execution Studio → Publish Queue**
   - Complete publish onboarding steps (OAuth, simulate)
   - Run **paper trading tick** if signals pending
3. Optional: Telegram digest at **07:30 UTC** when bot token + chat ID configured in tenant connectors

### Publish hooks

Verified publish packs auto-generate **hook variants** (curiosity, number, POV, etc.) — visible in Publish Queue for A/B testing before live post.

## Env flags (`.env.prod`)

```bash
OPERATOR_LOOP_ENABLED=true
OPERATOR_LOOP_TELEGRAM_MORNING_ENABLED=true
PUBLISH_HOOK_VARIANTS_ENABLED=true
TRADING_COCKPIT_TELEGRAM_NOTIFY_ON_FILL=true
DUMP_SLEEP_ENABLED=true
MORNING_PUBLISH_PIPELINE_ENABLED=true
```

Safe defaults: all `true` except live publish/trading flags remain `false` until operator enables OAuth + live gates.

## Celery

| Task | Schedule | Purpose |
|------|----------|---------|
| `hive.operator_loop_morning_tick` | 07:30 UTC | Telegram morning digest |
| `hive.morning_publish_pipeline_tick` | 08:00 UTC | Trigger Life OS + content routines |

## Architecture

- **One bee, one job:** Operator Loop only *composes* existing verified subsystems — no duplicate business logic
- **Simulate-first:** publish approval and paper trading before real money
- **Human approval:** real trading requires `PREDICTION_MARKETS_LIVE_TRADING_ENABLED` + venue connectors

## Gate

```bash
./scripts/audit-operator-loop-gate.sh
```

Included in `./scripts/operator-release-gate.sh`.
