# Operator P0 — Close checklist

Last automated run: see `reports/operator/OPERATOR_LAUNCH_CHECKLIST_*.md`

## Status

| Track | Status |
|-------|--------|
| Dev Phase 0–6 + all P2 harness | ✅ Complete |
| Automated walkthrough (API + browser + session + command center) | ✅ `operator-launch-gate.sh` |
| HA/DR + host exposure | ✅ Evidence on disk |
| **Stripe live checkout** | ❌ **Out of scope** — removed from roadmap (solo operator; see `docs/SOLO_OPERATOR_MODE.md`) |
| **Hetzner abuse email** | ⏳ Draft ready — operator must send |
| Harness automation (GitHub webhook, Forager cron) | ⏳ Optional — `./scripts/operator-harness-env-prep.sh` |

## One command — full operator status

```bash
./scripts/operator-launch-checklist.sh
# Writes reports/operator/OPERATOR_LAUNCH_CHECKLIST_*.md

# Or all prep scripts at once:
./scripts/operator-p0-prep-all.sh
```

## P0 order (human)

> **Stripe:** not on the roadmap. Billing endpoints remain in code for future commercial use but require no operator action.

### 1. Hetzner (manual)

**Guide:** `docs/OPERATOR_HETZNER_SEND.md`

```bash
./scripts/operator-hetzner-copy-email.sh   # refresh + full copy-paste body
# Send to abuse@hetzner.com
# Subject: Re: AbuseID 11B0286:23 — remediation completed
```

### 2. Harness env (Queen Maintainer / SCV automation)

```bash
./scripts/operator-harness-env-prep.sh
```

Add to `.env.prod` as needed:

| Variable | Purpose |
|----------|---------|
| `QUEEN_MAINTAINER_ENABLED=true` | Maintainer routine |
| `QUEEN_MAINTAINER_POST_MERGE_WEBHOOK_ENABLED=true` | Post-merge trigger |
| `QUEEN_MAINTAINER_GITHUB_WEBHOOK_SECRET` | GitHub HMAC |
| `QUEEN_MAINTAINER_POST_MERGE_TENANT_ID` | Tenant UUID |
| `FORAGER_INTELLIGENCE_LOOP_ENABLED=true` | Daily intelligence scan |
| `SLACK_WEBHOOK_URL` | Alertmanager → Slack |

GitHub repo webhook — **copy-paste guide:** `docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md`

```bash
./scripts/operator-resolve-tenant-id.sh
./scripts/operator-github-webhook-prep.sh
```

- URL: `https://queenswarm.love/api/v1/queen-maintainer/github-webhook`
- Events: Pull requests (+ optional push to main)

Then redeploy: `ENV_FILE=.env.prod ./scripts/deploy-prod.sh`

### 3. Launch gate evidence

```bash
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh
./scripts/operator-final-handoff.sh
```

## Stripe (optional — not on roadmap)

Legacy docs only if you later enable commercial billing:

- `docs/OPERATOR_STRIPE_SETUP.md`
- `docs/OPERATOR_STRIPE_DASHBOARD_WALKTHROUGH.md`

## References

- `docs/OPERATOR_HETZNER_SEND.md`
- `docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md`
- `docs/TOMORROW_OPERATOR_RUNBOOK.md`
- `docs/AUTHENTICATED_PROD_WALKTHROUGH.md`
- `docs/MISSION_EXECUTION_BACKLOG.md`
- `docs/SOLO_OPERATOR_MODE.md`

## Re-run automated evidence only

```bash
SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-final-handoff.sh
```
