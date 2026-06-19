# Personal OS Roadmap — Focused (post Gumroad purge)

> **Scope:** queenswarm.love solo operator daily stack. Gumroad / MK6 cash funnel / export-batch lanes **removed from app code** (2026-06). Archived commercial docs live under `PERSONAL_OS_MODE` notes in git history only.

## What moves you forward (keep & use daily)

| Area | Routes | Why it matters |
|------|--------|----------------|
| **Mission Home + Jarvis** | `/tasks` | Morning brief, process rail, next actions |
| **Kanban triage** | `/tasks` | Plan → work handoff |
| **Supervisor + skill picker** | `/agents#sessions` | Run agents with verified library skills |
| **Skill Factory (in-app)** | `/apps-tools/skill-factory` | Research → Queue → Library → attach in Sessions |
| **Ballroom Dump & Sleep** | `/ballroom` | Evening capture + learn rail |
| **Foragers / Hive Mind** | `/foragers` | Background scrape → curated memory |
| **Knowledge / Brain Pack** | `/knowledge#memory` | Curated memory — **P0 operator blocker** if empty |
| **Weekly compound / reflection** | `/knowledge`, Mission Home strips | Long-horizon learnings without revenue funnel |
| **Life OS calendar** | Settings + Mission Home | Optional but high value when connected |
| **Autopilot harness** | `/settings/harness` | Routines, four lanes, digest |

## Operator readiness (P0 — not missing POS waves)

1. **LLM keys** — Settings → AI · LLM keys + Skill Factory smoke test  
2. **Brain Pack** — Knowledge → Memory / Settings → AI harness  
3. **First supervisor session** — `/agents#sessions` with ≥1 verified library skill  
4. **Daily habit** — tasks → sessions → ballroom → foragers (background)

## Removed from product (do not re-add without explicit decision)

- Gumroad draft/publish API, webhooks, purchase unlock, post-purchase onboarding  
- Mission Home: Factory Launch, Revenue Funnel, Catalog Wave widgets  
- Skill Factory **Launch** tab, export-batch, Gumroad CTAs  
- MK6/MK7/REV4–REV12 revenue automation waves  
- Operator scripts: `prepare-gumroad-*`, `operator-gumroad-*`, `factory-first-revenue-*`

## Optional / later (only if you want them — not blockers)

| Item | Notes |
|------|-------|
| Analytics depth | Useful if you track time ROI |
| Vertical research packs | Skill Factory seeds, not Gumroad catalog waves |
| Marketing site (letagentscook) | Separate from Personal OS; may keep filesystem manifests |
| Trading cockpit | Off in Personal OS |
| HA drill / secrets rotation / Grafana | P2/P3 ops |

## Verification commands

```bash
./scripts/audit-personal-os-in-app-skills-gate.sh
./scripts/operator-personal-os-verify.sh
./scripts/ci-local.sh all
```

## Autopilot priority stack (unchanged)

1. Operator readiness (LLM + Brain Pack + first session)  
2. Skill Factory in-app polish (queue drain, library attach UX)  
3. OS features ≤2d only if they unblock daily use  

**No more Gumroad/revenue waves** unless product direction explicitly changes.
