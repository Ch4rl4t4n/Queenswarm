# Tomorrow Operator Runbook — Audit

Quick checklist for the morning session. **Read-only audits first**, then manual walkthrough.

**All-in-one prep (recommended):**

```bash
./scripts/operator-p0-prep-all.sh
# Hetzner + tenant UUID + GitHub webhook + harness env + launch checklist
```

See also: `docs/OPERATOR_LAUNCH_INDEX.md`, `docs/OPERATOR_P0_CLOSE.md`, `docs/OPERATOR_HARNESS_WEBHOOK_SETUP.md`

## 1. Health snapshot (~5 min)

```bash
cd /root/Queenswarm

# Unified mission readiness (Phase 0 + 1 + 2 + perf)
./scripts/mission-readiness-audit.sh

# All-in-one automated slice (readiness + operator gates + prod walkthrough [3b user JWT auto] + responsive E2E)
# SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-launch-gate.sh

# Operator P0 gates (walkthrough doc + operator scripts)
./scripts/operator-gates-audit.sh

# Automated walkthrough evidence (writes reports/walkthrough/*.json)
./scripts/walkthrough-evidence.sh

# Or individually:
./scripts/mission-phase0-audit.sh
./scripts/mission-phase1-audit.sh
./scripts/mission-phase2-audit.sh

# Container health
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml --env-file .env.prod ps

# Edge probe
curl -sS -o /dev/null -w "health:%{http_code}\n" https://queenswarm.love/health
```

Expected: all core containers `healthy`, health returns non-502.

## 2. Full audit (~30–45 min)

```bash
# Security exposure
./scripts/audit-host-exposure.sh

# Disk (dry-run; APPLY=1 prunes dev stack + build cache — freed ~173GB on 2026-05-21)
./scripts/audit-disk-cleanup.sh
# If disk >80%: docker builder prune -af   # safe; does not touch queenswarm_prod containers

# All-in-one automated operator slice + evidence:
# SKIP_E2E=1 SKIP_RESPONSIVE_E2E=1 ./scripts/operator-final-handoff.sh
```

Review in app: **Settings → Capabilities · atlas** — confirm roadmap phases match this doc.

## 3. Dev status (2026-05-21)

| Track | Status |
|-------|--------|
| Phase 0 — wizard, gates, widgets | ✅ Shipped |
| Phase 1 — marketplace, ROI, UGC, badges | ✅ Shipped |
| Phase 2 — enterprise, sub-swarm mind | ✅ Shipped |
| Performance — cockpit bundle + WS delta | ✅ Shipped |
| Prod walkthrough sign-off | ✅ Automated — `./scripts/operator-final-handoff.sh` |
| Billing checkout runtime | ✅ Removed from active surface |

Deploy stack (after audit green):

```bash
./scripts/mission-readiness-audit.sh && \
REQUIRE_VOICE_READY=0 POST_DEPLOY_HEALTH=1 ./scripts/deploy-prod.sh
```

Deploy frontend only (safe):

```bash
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod build frontend && \
docker compose -p queenswarm_prod -f docker-compose.base.yml -f docker-compose.prod.yml \
  --env-file .env.prod up -d frontend --no-deps --wait
```

**Never** run `docker compose up` without `--env-file .env.prod` on production.

## 4. If something breaks

| Symptom | Fix |
|---------|-----|
| 502 Bad Gateway | Backend/frontend down — redeploy with `.env.prod` |
| Postgres auth error | Password mismatch — use `--env-file .env.prod` |
| PWA stale UI | Hard refresh; SW cache version in `frontend/public/sw.js` |

Logs:

```bash
docker compose -p queenswarm_prod logs --tail=80 backend frontend nginx
```
