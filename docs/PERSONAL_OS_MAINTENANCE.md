# Personal OS — maintenance audits & operator rhythm

Updated: 2026-06-05

Personal OS is the **solo operator daily stack** without revenue funnel, Gumroad widgets, trading cockpit, or beta lab noise. Toggle: `PERSONAL_OS_MODE_ENABLED=true` (requires `SOLO_MODE_ENABLED=true`).

Apply preset: `./scripts/apply-solo-mode.sh` (merges `.env.solo.example` → `.env.prod` + redeploy).

## Daily operator workflow (target)

| Time | Route | Action |
|------|-------|--------|
| Morning | `/tasks` | Mission Home brief + Life OS calendar + kanban triage |
| Day | `/agents` or Marketing lane | Supervisor sessions / publish queue |
| Evening | `/ballroom` | Dump & Sleep overnight ingest |
| Background | `/foragers` | Scrape → Hive Mind |

## Automated gates (CI + weekly operator)

| Audit | Command | Cadence | Checks |
|-------|---------|---------|--------|
| **Personal OS shell** | `./scripts/audit-personal-os-gate.sh` | Every PR touching nav/platform/mission-home | Preset wiring, auth/me flag, revenue widget strip |
| **Personal OS tests** | `RUN_PERSONAL_OS_TESTS=1 ./scripts/audit-personal-os-gate.sh` | Weekly / pre-deploy | `test_personal_os_mode_unit`, mission home |
| **Life OS calendar** | `./scripts/audit-life-os-gate.sh` | Weekly / after Mission Home changes | Calendar strip + planner wiring |
| **Autopilot** | `./scripts/audit-autopilot-gate.sh` | Weekly / after harness or lanes changes | My 3 Bees + Four Lanes + digest inbox |
| **Skill Factory lite** | `./scripts/audit-skill-factory-lite-gate.sh` | After Skill Factory UI changes | Gumroad Launch tab hidden in Personal OS |
| **Weekly verify (all POS)** | `./scripts/operator-personal-os-verify.sh` | Weekly operator ritual | All POS gates + prod flags + API smoke |
| **POS-G leak gate** | `./scripts/audit-personal-os-dead-code-gate.sh` | After POS-G UI changes | Factory redirect · Mission Home commercial gate |
| **POS-G inventory** | `./scripts/audit-personal-os-dead-code-inventory.sh` | Before G4–G5 deletion | Read-only commercial route list |
| **Jarvis Intelligence (POS-H)** | `./scripts/audit-jarvis-intelligence-gate.sh` | After Mission Home advisor changes | Jarvis strip · weak signal · agent quality · research project |
| **POS-J compound wave** | `./scripts/audit-personal-os-compound-gate.sh` | After POS-J changes | Weekly gardener · email drafts · research rank · faceless cut |
| **POS-K adoption wave** | `./scripts/audit-personal-os-adoption-gate.sh` | After POS-J UI wiring | Compound panel · Approval Inbox · Faceless cut · Research dedupe |
| **POS-L daily flow** | `./scripts/audit-personal-os-daily-flow-gate.sh` | After POS-L changes | Cockpit shortcut · Telegram pending pings |
| **POS-M memory adoption** | `./scripts/audit-personal-os-memory-adoption-gate.sh` | After MEM2 UX wiring | Cited recall shortcut · Jarvis nudge |
| **POS-N second brain** | `./scripts/audit-personal-os-second-brain-adoption-gate.sh` | After SB/LOOP UX wiring | Wiki captures · closed loops · MOC tick |
| **POS-O agent loop** | `./scripts/audit-personal-os-agent-loop-adoption-gate.sh` | After AL1 UX wiring | Loop timeline strip · Jarvis nudge · deep-link scroll |
| **POS-P closed loop verify** | `./scripts/audit-personal-os-closed-loop-verify-gate.sh` | After AL2/LOOP2 UX wiring | Tool outcomes · guardrails strip · Jarvis verify |
| **POS-Q intel / goldmine** | `./scripts/audit-personal-os-intel-adoption-gate.sh` | After DG3 UX wiring | Goldmine strip · Jarvis delta nudge · foragers anchor |
| **Second brain SB1–4** | `./scripts/audit-second-brain-gate.sh` | Weekly | Capture approve · connection intelligence · ⌘K wiki |
| **MEM5 project tags** | `./scripts/audit-memory-project-tags-gate.sh` | After memory tag changes | Client/project recall slice |
| **Solo daily plan** | `./scripts/audit-solo-daily-plan-gate.sh` | Weekly | Morning brief + kanban wiring |
| **Social publish** | `./scripts/audit-social-publish-gate.sh` | Before enabling live publish | OAuth + simulate-first queue |
| **Publish queue** | `./scripts/audit-publish-queue-gate.sh` | Before Marketing Team Phase B | Queue + calendar backend |
| **Single admin** | `./scripts/audit-single-admin-gate.sh` | After auth changes | One tenant invariant |
| **Full CI** | `./scripts/ci-local.sh all` | Before push to `main` | Backend 80% cov + e2e subset |

## Flag consistency checklist (prod)

After `./scripts/apply-solo-mode.sh`:

```bash
docker exec queenswarm_prod-backend-1 python -c "
from app.core.config import settings
keys = [
  'solo_mode_enabled', 'personal_os_mode_enabled',
  'revenue_funnel_mission_home_enabled', 'catalog_wave_mission_home_enabled',
  'factory_launch_mission_home_enabled', 'routines_enabled', 'trading_cockpit_enabled',
]
for k in keys: print(k, getattr(settings, k))
"
```

Expected Personal OS prod:

- `personal_os_mode_enabled=True`
- `revenue_funnel_*` / `catalog_wave_*` / `factory_launch_mission_home_*` → `False`
- `routines_enabled=True` (Phase E — enable Four Lanes cron)
- `trading_cockpit_enabled=False`

## Phase roadmap (implementation)

| Phase | Scope | Status |
|-------|-------|--------|
| **POS-A** | Hide preset + strip Mission Home revenue widgets + nav cleanup | ✅ This ship |
| **POS-B** | Marketing Team unified module (post-bridge UX + calendar) | ✅ Shipped |
| **POS-C** | Faceless content pipeline (idea → post/video → schedule) | ✅ Shipped |
| **POS-D** | Life OS — Calendar → daily planner in Mission Home | ✅ Shipped |
| **POS-E** | Autopilot — routines cron + My 3 Bees + Four Lanes | ✅ Shipped |
| **POS-F** | Skill Factory lite — strip Gumroad tabs | ✅ Shipped |
| **POS-G** | G1–G5 dead-code leak gates + commercial API/page archive | ✅ Shipped |
| **POS-H** | Intelligence Wave — Jarvis advisor · research project · weak signals · agent quality | ✅ Shipped · `./scripts/audit-jarvis-intelligence-gate.sh` |
| **POS-I** | I1–I5 Intelligence Wave follow-up (Jarvis · research · brand · MCP) | ✅ komplet |
| **POS-J** | J1–J5 compound automation (weekly gardener · email drafts · research rank · faceless cut) | ✅ Shipped |
| **POS-K** | K1–K5 adoption wave (UI wiring for POS-J — Knowledge · Cockpit · Faceless · Research dedupe) | ✅ Shipped |
| **POS-L** | L1–L3 daily flow (Mission Home → Cockpit · Telegram on pending drafts) | ✅ Shipped |
| **POS-M** | M1–M4 memory adoption (Cited recall daily flow · Jarvis nudge) | ✅ Shipped |
| **POS-N** | N1–N4 second brain adoption (Wiki captures · closed loops · Jarvis) | ✅ Shipped |
| **POS-O** | O1–O4 agent loop adoption (Mission Home strip · Jarvis · deep-link scroll) | ✅ Shipped |
| **POS-P** | P1–P4 closed loop verify (AL2 tool outcomes · LOOP2 guardrails · Jarvis) | ✅ Shipped |
| **POS-Q** | Q1–Q4 intel adoption (DG3 goldmine strip · Jarvis · foragers anchor) | ✅ Shipped |

## Rollback

1. Set `PERSONAL_OS_MODE_ENABLED=false` in `.env.prod`
2. Optionally restore revenue widgets: `REVENUE_FUNNEL_MISSION_HOME_ENABLED=true` etc.
3. `./scripts/deploy-prod.sh --env-file .env.prod`

Full commercial multi-tenant: `SOLO_MODE_ENABLED=false` + redeploy (not recommended for solo host).
